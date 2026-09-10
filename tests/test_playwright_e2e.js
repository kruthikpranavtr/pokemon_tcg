const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const http = require('http');

const SERVER_URL = 'http://127.0.0.1:8000';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function checkServerReady(url, maxAttempts = 30) {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const interval = setInterval(() => {
            attempts++;
            const req = http.get(url, (res) => {
                if (res.statusCode >= 200 && res.statusCode < 400) {
                    clearInterval(interval);
                    resolve(true);
                }
            });
            req.on('error', () => {
                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    reject(new Error('Server at ' + url + ' not responding after ' + maxAttempts + ' attempts'));
                }
            });
            req.end();
        }, 1000);
    });
}

async function runE2ETests() {
    console.log('====================================================');
    console.log('   POKEMON TCG PLAYWRIGHT COMPLETE UI E2E TEST SUITE');
    console.log('====================================================');

    console.log('\n[1/8] Verifying backend server is available at ' + SERVER_URL + '...');
    try {
        await checkServerReady(SERVER_URL, 10);
        console.log('  [PASS] Backend server is online and responding.');
    } catch (e) {
        console.error('  [FAIL] Backend server not found at ' + SERVER_URL);
        process.exit(1);
    }

    console.log('\n[2/8] Launching Chromium browser with Playwright...');
    const CHROME_PATH = 'C:/Users/jashwanth ck/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe';
    const browser = await chromium.launch({
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1400, height: 900 }
    });
    const page = await context.newPage();

    let lastDialogMessage = '';
    page.on('dialog', async dialog => {
        lastDialogMessage = dialog.message();
        console.log('  [Dialog/Alert caught]: "' + lastDialogMessage + '"');
        await dialog.accept();
    });

    try {
        console.log('\n[3/8] Navigating to Pokemon TCG Dashboard...');
        await page.goto(SERVER_URL, { waitUntil: 'networkidle' });
        
        const title = await page.title();
        console.log('  Page title: "' + title + '"');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial_page.png') });
        console.log('  Screenshot saved: 01_initial_page.png');

        // Test Registration
        console.log('\n[4/8] Testing Trainer Registration and Authentication UI...');
        const regBtn = page.locator('button:has-text("CREATE ACCOUNT")').first();
        await regBtn.click();
        await page.waitForSelector('#auth-modal', { state: 'visible' });

        const testTrainerName = 'Trainer_' + Date.now().toString().slice(-6);
        const testEmail = testTrainerName.toLowerCase() + '@pokemon.test';
        const testPass = 'PikachuMaster2026!';

        await page.fill('#reg-username', testTrainerName);
        await page.fill('#reg-email', testEmail);
        await page.fill('#reg-pass', testPass);
        await page.fill('#reg-confirm-pass', testPass);
        
        await page.click('#form-register button:has-text("CREATE ACCOUNT")');
        await page.waitForTimeout(1000);

        // Verify logged-in state
        const usernameDisplay = await page.locator('#header-username').textContent();
        console.log('  Logged-in username displayed in header: "' + usernameDisplay + '"');
        if (!usernameDisplay.includes(testTrainerName)) {
            throw new Error('Expected header username to contain "' + testTrainerName + '", got "' + usernameDisplay + '"');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_logged_in.png') });
        console.log('  [PASS] User registered and authenticated successfully. Screenshot saved: 02_logged_in.png');

        // Test Booster Pack Opening
        console.log('\n[5/8] Testing 8-Card Booster Pack Opening & 3D Flip Reveal...');
        await page.click('#tab-btn-pack', { force: true });
        await page.waitForSelector('#view-pack', { state: 'visible' });

        const openPackBtn = page.locator('#btn-open-pack');
        await openPackBtn.click({ force: true });
        
        await page.waitForSelector('.card-flip-wrapper', { state: 'visible', timeout: 10000 });
        const cardFlips = await page.locator('.card-flip-wrapper').all();
        console.log('  Booster cards rendered in stage: ' + cardFlips.length + ' cards (Expected: 8)');
        if (cardFlips.length !== 8) {
            throw new Error('Expected exactly 8 booster cards, found ' + cardFlips.length);
        }

        const revealAllBtn = page.locator('button:has-text("REVEAL ALL CARDS")');
        await revealAllBtn.click({ force: true });
        await page.waitForTimeout(2000);

        const flippedCount = await page.locator('.card-flip-wrapper.flipped').count();
        console.log('  Flipped cards revealed: ' + flippedCount + '/8');
        if (flippedCount !== 8) {
            throw new Error('Expected all 8 cards to be flipped, got ' + flippedCount);
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_pack_opened_8_cards.png') });
        console.log('  [PASS] Booster pack opened and all 8 cards revealed. Screenshot saved: 03_pack_opened_8_cards.png');

        // Test Available Cards / Collection View
        console.log('\n[6/8] Testing "Your Available Cards" Collection Grid...');
        await page.click('#tab-btn-cards', { force: true });
        await page.waitForSelector('#view-cards', { state: 'visible' });

        const ownedCards = await page.locator('#owned-cards-grid > div').count();
        console.log('  Cards displayed in personal collection: ' + ownedCards);
        if (ownedCards === 0) {
            throw new Error('Expected owned cards grid to display cards, but it was empty.');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_collection_grid.png') });
        console.log('  [PASS] Collection grid verified. Screenshot saved: 04_collection_grid.png');

        // Test Starting Match Arena
        console.log('\n[7/8] Testing Battle Setup and Opponent Bench Count...');
        const startBattleBtn = page.locator('#btn-start-4cards');
        await startBattleBtn.click({ force: true });
        await page.waitForSelector('#view-match', { state: 'visible' });

        // REQUIREMENT 1 VERIFICATION: Opponent bench has exactly 3 Pokemon
        const oppBenchCards = await page.locator('#opp-bench-view > div').all();
        console.log('  --> Opponent Bench Pokemon Count: ' + oppBenchCards.length + ' (Expected: EXACTLY 3)');
        
        for (let i = 0; i < oppBenchCards.length; i++) {
            const text = await oppBenchCards[i].textContent();
            console.log('      Opponent Bench Slot #' + (i+1) + ': ' + text.replace(/\s+/g, ' ').trim());
        }

        if (oppBenchCards.length !== 3) {
            throw new Error('FAILURE: Opponent bench must have EXACTLY 3 Pokemon! Found ' + oppBenchCards.length);
        }
        console.log('  [PASS] REQUIREMENT 1 VERIFIED: Opponent bench has exactly 3 Pokemon!');

        // Player bench count verification
        const playerBenchCards = await page.locator('#player-bench-view > div').count();
        console.log('  --> Player Bench Pokemon Count: ' + playerBenchCards + ' (Expected: 3)');
        if (playerBenchCards !== 3) {
            throw new Error('FAILURE: Player bench must also have 3 Pokemon! Found ' + playerBenchCards);
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_battle_arena_3_bench.png') });
        console.log('  Screenshot saved: 05_battle_arena_3_bench.png');

        // REQUIREMENT 2 VERIFICATION: Draw Deck Card button works once per turn
        console.log('\n[8/8] Testing DRAW DECK CARD 1-Per-Turn Rule...');
        const drawBtn = page.locator('#btn-claim-deck-card');
        
        const isInitiallyDisabled = await drawBtn.isDisabled();
        const initialBtnText = await drawBtn.textContent();
        console.log('  Initial Draw Button text: "' + initialBtnText.replace(/\s+/g, ' ').trim() + '", disabled: ' + isInitiallyDisabled);
        if (isInitiallyDisabled) {
            throw new Error('Draw button should initially be enabled on Player Turn 1');
        }

        const initialHandCount = await page.locator('#player-hand-view > div').count();
        const initialDeckCount = parseInt(await page.locator('#p-deck-count').textContent(), 10);
        console.log('  Initial Hand: ' + initialHandCount + ' cards | Deck: ' + initialDeckCount + ' cards');

        console.log('  Action: Clicking DRAW DECK CARD (1st draw of the turn)...');
        await drawBtn.click();
        await page.waitForTimeout(600);

        const newHandCount = await page.locator('#player-hand-view > div').count();
        const newDeckCount = parseInt(await page.locator('#p-deck-count').textContent(), 10);
        console.log('  After 1st Draw -> Hand: ' + newHandCount + ' cards (+' + (newHandCount - initialHandCount) + ') | Deck: ' + newDeckCount + ' cards (-' + (initialDeckCount - newDeckCount) + ')');

        if (newHandCount !== initialHandCount + 1) {
            throw new Error('Expected hand count to increase by 1 (from ' + initialHandCount + ' to ' + (initialHandCount + 1) + '), got ' + newHandCount);
        }
        if (newDeckCount !== initialDeckCount - 1) {
            throw new Error('Expected deck count to decrease by 1 (from ' + initialDeckCount + ' to ' + (initialDeckCount - 1) + '), got ' + newDeckCount);
        }

        const isDisabledAfterDraw = await drawBtn.isDisabled();
        const btnTextAfterDraw = await drawBtn.textContent();
        console.log('  Draw Button text after draw: "' + btnTextAfterDraw.replace(/\s+/g, ' ').trim() + '", disabled: ' + isDisabledAfterDraw);
        
        if (!isDisabledAfterDraw) {
            throw new Error('FAILURE: Draw button MUST be disabled after drawing once in a turn!');
        }
        if (!btnTextAfterDraw.includes('DECK CARD DRAWN')) {
            throw new Error('FAILURE: Draw button should show "DECK CARD DRAWN", got "' + btnTextAfterDraw + '"');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_draw_card_disabled.png') });
        console.log('  [PASS] Draw button successfully disabled for this turn. Screenshot saved: 06_draw_card_disabled.png');

        console.log('  Action: Attempting 2nd draw in same turn (via direct JS invocation)...');
        lastDialogMessage = '';
        await page.evaluate(() => {
            if (typeof claimRandomDeckCard === 'function') {
                claimRandomDeckCard();
            }
        });
        await page.waitForTimeout(500);

        const handAfter2ndAttempt = await page.locator('#player-hand-view > div').count();
        console.log('  Hand count after 2nd draw attempt: ' + handAfter2ndAttempt + ' (Must remain ' + newHandCount + ')');
        if (handAfter2ndAttempt !== newHandCount) {
            throw new Error('FAILURE: Hand count increased on 2nd draw in same turn! Hand: ' + handAfter2ndAttempt);
        }
        console.log('  Blocked notification dialog caught: "' + lastDialogMessage + '"');
        console.log('  [PASS] REQUIREMENT 2 VERIFIED: DRAW DECK CARD works strictly once per turn!');

        // Verify Next Turn re-enables the draw button
        console.log('\n[Bonus] Verifying that Turn 2 re-enables the Draw Deck Card button...');
        await page.click('#btn-add-energy-main');
        await page.waitForTimeout(300);

        const attackBtn = page.locator('.btn-attack').first();
        if (await attackBtn.isVisible()) {
            console.log('  Player attacking with active Pokemon to pass turn to Opponent AI...');
            await attackBtn.click();

            console.log('  Waiting for Opponent AI turn to process and switch back to Player...');
            await page.waitForFunction(() => {
                const banner = document.getElementById('match-status-banner');
                return banner && banner.textContent.includes('YOUR TURN') && !window.IS_AI_PROCESSING;
            }, { timeout: 15000 });

            await page.waitForTimeout(800);

            const isTurn2Enabled = !(await drawBtn.isDisabled());
            const turn2BtnText = await drawBtn.textContent();
            console.log('  Turn 2 Draw Button status: enabled = ' + isTurn2Enabled + ', text = "' + turn2BtnText.replace(/\s+/g, ' ').trim() + '"');
            
            if (!isTurn2Enabled) {
                throw new Error('FAILURE: Draw button should be re-enabled on Turn 2!');
            }
            console.log('  [PASS] Turn 2 reset verified: Draw button is re-enabled for 1 new draw!');
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_turn_2_draw_reenabled.png') });
        }

        console.log('\n====================================================');
        console.log('  ALL PLAYWRIGHT UI TESTS PASSED SUCCESSFULLY!');
        console.log('====================================================');

    } catch (err) {
        console.error('\nTEST FAILED WITH ERROR:', err.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ERROR_failure.png') });
        throw err;
    } finally {
        await browser.close();
    }
}

runE2ETests().catch((e) => {
    console.error(e);
    process.exit(1);
});
