const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SERVER_URL = 'http://127.0.0.1:8000';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runWeaknessAndArtPlaywrightTest() {
    console.log('================================================================================');
    console.log('  TEST: CARD ART DISPLAY, WEAKNESS EVALUATION, SWITCH, & TURN-START DECK DRAW  ');
    console.log('================================================================================');

    const CHROME_PATH = 'C:/Users/jashwanth ck/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe';
    const browser = await chromium.launch({
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1440, height: 960 }
    });
    const page = await context.newPage();

    let lastDialogMessage = '';
    page.on('dialog', async dialog => {
        lastDialogMessage = dialog.message();
        console.log('  [Alert Intercepted]: "' + lastDialogMessage + '"');
        await dialog.accept();
    });

    try {
        console.log('\n[Phase 1] Navigating to Pokemon TCG Match Arena...');
        await page.goto(SERVER_URL, { waitUntil: 'networkidle' });
        await page.waitForSelector('#view-match', { state: 'visible' });

        // Phase 2: Verify Active Card Art Display
        console.log('\n[Phase 2] Verifying Main Pokémon Image Display in Active Cards...');
        const playerActiveImg = page.locator('#player-active-view .active-card-img-box img');
        const oppActiveImg = page.locator('#opp-active-view .active-card-img-box img');

        await playerActiveImg.waitFor({ state: 'visible', timeout: 8000 });
        await oppActiveImg.waitFor({ state: 'visible', timeout: 8000 });

        const playerImgSrc = await playerActiveImg.getAttribute('src');
        const oppImgSrc = await oppActiveImg.getAttribute('src');
        console.log('  Player Active Image URL:', playerImgSrc);
        console.log('  Opponent Active Image URL:', oppImgSrc);

        if (!playerImgSrc || !oppImgSrc) {
            throw new Error('Active Pokemon cards must display image src!');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '17_active_pokemon_card_art.png') });
        console.log('  [Screenshot 17] Saved: 17_active_pokemon_card_art.png');

        // Phase 3: Setup Bulbasaur (Grass, weak to Fire) vs Pikachu with Charmander & Snorlax in hand
        console.log('\n[Phase 3] Configuring Matchup: Opponent Bulbasaur (Grass), Hand: Charmander, Snorlax, Switch, Energy...');
        await page.evaluate(() => {
            CURRENT_MATCH_STATE.player.active_spot = { name: "Pikachu", current_hp: 50, max_hp: 70, attached_energy: [] };
            CURRENT_MATCH_STATE.player.bench = [];
            CURRENT_MATCH_STATE.player.hand = ["Charmander", "Snorlax", "Switch", "Basic Fire Energy"];
            CURRENT_MATCH_STATE.player.deck = ["Potion", "Ultra Ball", "Professor's Research"];
            CURRENT_MATCH_STATE.opponent.active_spot = { name: "Bulbasaur", current_hp: 70, max_hp: 70, attached_energy: [] };
            CURRENT_MATCH_STATE.opponent.bench = [];
            CURRENT_MATCH_STATE.energy_attached_this_turn = false;
            CURRENT_MATCH_STATE.card_drawn_this_turn = false;
            CURRENT_ROUTE_STEP_INDEX = 0;
            updateMatchView(CURRENT_MATCH_STATE);
        });

        // Compute Strategic AI Winning Route
        console.log('\n[Phase 4] Computing Strategic AI Winning Route...');
        await page.evaluate(async () => {
            await fetchStrategicAiAnalysis('BALANCED');
        });

        await page.waitForFunction(() => {
            const steps = document.querySelectorAll('#left-route-steps > div');
            return steps.length >= 3;
        }, { timeout: 15000 });

        const stepsCount = await page.locator('#left-route-steps > div').count();
        console.log('  Winning Route Steps count: ' + stepsCount);
        let benchStepFound = false;
        let switchStepFound = false;

        for (let i = 1; i <= stepsCount; i++) {
            const stepText = await page.locator('#left-route-steps > div:nth-child(' + i + ')').textContent();
            console.log('    Step ' + i + ': ' + stepText.replace(/\s+/g, ' ').trim());
            if (stepText.includes('Charmander') && stepText.includes('Win Possibility as Main')) {
                benchStepFound = true;
            }
            if (stepText.includes('Switch') && stepText.includes('Charmander')) {
                switchStepFound = true;
            }
        }

        if (!benchStepFound) {
            throw new Error('AI must evaluate hand Pokemon and recommend benching Charmander for weakness matchup!');
        }
        if (!switchStepFound) {
            throw new Error('AI must sequence Switch to promote Charmander to exploit opponent weakness!');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '18_weakness_evaluated_winning_route.png') });
        console.log('  [Screenshot 18] Saved: 18_weakness_evaluated_winning_route.png');

        const executeBtn = page.locator('#btn-execute-ai');

        // CLICK 1: Bench Charmander
        console.log('\n[Phase 5] [CLICK 1] Executing Step 1: Bench Charmander...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        const benchPokemon = await page.evaluate(() => CURRENT_MATCH_STATE.player.bench.map(b => b.name));
        console.log('  Player Bench after Step 1:', benchPokemon);
        if (!benchPokemon.includes('Charmander')) {
            throw new Error('Charmander must be placed onto bench!');
        }

        // Verify bench thumbnail art
        const benchImg = page.locator('#player-bench-view img');
        await benchImg.waitFor({ state: 'visible', timeout: 5000 });
        const benchImgSrc = await benchImg.getAttribute('src');
        console.log('  Benched Charmander thumbnail URL:', benchImgSrc);

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '19_charmander_benched_with_art.png') });
        console.log('  [Screenshot 19] Saved: 19_charmander_benched_with_art.png');

        // CLICK 2: Tactical Switch to promote Charmander
        console.log('\n[Phase 6] [CLICK 2] Executing Step 2: Tactical Switch to promote Charmander...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        const activeAfterSwitch = await page.evaluate(() => CURRENT_MATCH_STATE.player.active_spot.name);
        console.log('  Player Active Spot after Switch:', activeAfterSwitch);
        if (activeAfterSwitch !== 'Charmander') {
            throw new Error('Switch should have promoted Charmander to Active Spot!');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '20_switch_promoted_charmander.png') });
        console.log('  [Screenshot 20] Saved: 20_switch_promoted_charmander.png');

        // CLICK 3: Attach Energy
        console.log('\n[Phase 7] [CLICK 3] Executing Step 3: Attach Energy...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        // CLICK 4: Offensive Strike with Weakness Multiplier
        console.log('\n[Phase 8] [CLICK 4] Executing Step 4: Offensive Strike with Weakness (2x)...');
        const deckCountBeforeStrike = await page.evaluate(() => (CURRENT_MATCH_STATE.player.deck || []).length);
        const handCountBeforeStrike = await page.evaluate(() => (CURRENT_MATCH_STATE.player.hand || []).length);
        console.log('  Player Deck count before turn concludes:', deckCountBeforeStrike);
        console.log('  Player Hand count before turn concludes:', handCountBeforeStrike);

        await executeBtn.click();
        console.log('  Offensive strike launched. Waiting for Opponent AI turn and Turn 2 transition...');
        await page.waitForTimeout(3000);

        // Phase 9: Verify Automatic Turn-Start Card Draw
        console.log('\n[Phase 9] Verifying Turn-Start Automatic Card Draw from Deck...');
        const deckCountTurn2 = await page.evaluate(() => (CURRENT_MATCH_STATE.player.deck || []).length);
        const handCountTurn2 = await page.evaluate(() => (CURRENT_MATCH_STATE.player.hand || []).length);
        const combatLog = await page.evaluate(() => CURRENT_MATCH_STATE.match_log);
        const turnDrawLog = combatLog.find(l => l.includes('Start Draw: Took 1 card'));

        console.log('  Player Deck count on Turn 2:', deckCountTurn2);
        console.log('  Player Hand count on Turn 2:', handCountTurn2);
        console.log('  Turn Draw Log Entry:', turnDrawLog);

        if (deckCountTurn2 >= deckCountBeforeStrike) {
            throw new Error('Player deck should have decreased by 1 on turn-start draw!');
        }
        if (!turnDrawLog) {
            throw new Error('Combat log must record turn-start card draw!');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '21_turn2_automatic_deck_draw.png') });
        console.log('  [Screenshot 21] Saved: 21_turn2_automatic_deck_draw.png');

        console.log('\n================================================================================');
        console.log('  SUCCESS: ALL 4 USER REQUIREMENTS VERIFIED AND PASSED VIA PLAYWRIGHT!');
        console.log('================================================================================');

    } catch (err) {
        console.error('\nTEST FAILED:', err.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ERROR_weakness_and_art_failure.png') });
        throw err;
    } finally {
        await browser.close();
    }
}

runWeaknessAndArtPlaywrightTest().catch(e => {
    console.error(e);
    process.exit(1);
});
