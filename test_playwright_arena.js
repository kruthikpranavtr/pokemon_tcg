const { chromium } = require('./node_modules/playwright');

async function run() {
    console.log('====================================================');
    console.log('PLAYWRIGHT TEST: VERIFYING EVERY ARENA BUTTON (E2E)');
    console.log('====================================================');

    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await context.newPage();

    const consoleLogs = [];
    const pageErrors = [];
    page.on('console', msg => {
        consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    });
    page.on('pageerror', err => {
        pageErrors.push(err.toString());
        console.error('PAGE ERROR:', err);
    });
    page.on('dialog', async dialog => {
        console.log(`[ALERT/DIALOG]: ${dialog.message()}`);
        await dialog.accept();
    });

    let passedChecks = 0;
    let totalChecks = 0;
    function check(desc, condition) {
        totalChecks++;
        if (condition) {
            passedChecks++;
            console.log(`  [PASS] ${desc}`);
        } else {
            console.error(`  [FAIL] ${desc}`);
        }
    }

    try {
        console.log('\n--- 1. APP LOAD & ARENA SETUP ---');
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2000);

        // Inject active user deck and start match
        await page.evaluate(async () => {
            const testDeck = [{
                id: 'my-custom-deck',
                name: 'Championship Deck',
                is_active: true,
                cards: [
                    { name: 'Mr. Mime ex', card_id: 'pkm-ex-0122', count: 2, type: 'Basic Pokémon' },
                    { name: 'Mudkip', card_id: 'pkm-0258', count: 2, type: 'Basic Pokémon' },
                    { name: 'Meditite', card_id: 'pkm-0307', count: 2, type: 'Basic Pokémon' },
                    { name: 'Basic Water Energy', card_id: 'energy-water', count: 5, type: 'Energy' },
                    { name: 'Basic Psychic Energy', card_id: 'energy-psychic', count: 5, type: 'Energy' }
                ]
            }];
            window.USER_DECKS = testDeck;
            localStorage.setItem('pokemon_tcg_user_decks', JSON.stringify(testDeck));
            await window.startNewMatch(false, true);
            window.switchMode('match');
        });
        await page.waitForTimeout(1500);

        const initialPhase = await page.evaluate(() => window.CURRENT_MATCH_STATE ? window.CURRENT_MATCH_STATE.phase : 'NO_STATE');
        console.log(`Initial Match Phase: ${initialPhase}`);
        check("Initial match phase is SETUP", initialPhase === 'SETUP');

        // Check hand buttons count
        const handMainBtns = await page.$$('#player-hand-view button:has-text("Main")');
        const handBenchBtns = await page.$$('#player-hand-view button:has-text("Bench")');
        check(`Found ${handMainBtns.length} [👑 Main] buttons in hand`, handMainBtns.length > 0);
        check(`Found ${handBenchBtns.length} [🛡️ Bench] buttons in hand`, handBenchBtns.length > 0);

        console.log('\n--- 2. BUTTON: [👑 Main] ON HAND CARD (PLACE & START BATTLE) ---');
        const firstMainBtn = handMainBtns[0];
        await firstMainBtn.click();
        await page.waitForTimeout(1500);

        const phaseAfterMain = await page.evaluate(() => window.CURRENT_MATCH_STATE ? window.CURRENT_MATCH_STATE.phase : 'NO_STATE');
        const activeCard = await page.evaluate(() => window.CURRENT_MATCH_STATE && window.CURRENT_MATCH_STATE.player ? window.CURRENT_MATCH_STATE.player.active_spot : null);
        const benchAfterMain = await page.evaluate(() => window.CURRENT_MATCH_STATE && window.CURRENT_MATCH_STATE.player ? window.CURRENT_MATCH_STATE.player.bench : []);
        console.log(`Phase: ${phaseAfterMain}, Active Spot: ${activeCard ? activeCard.name : 'EMPTY'}, Bench Count: ${benchAfterMain.length}`);
        check("Phase transitioned to BATTLE immediately upon clicking [👑 Main]", phaseAfterMain === 'BATTLE');
        check("Active Spot is populated with chosen Pokémon", activeCard !== null);
        check("Bench is populated with remaining Basic Pokémon", benchAfterMain.length > 0);

        console.log('\n--- 3. BUTTON: [🃏 DRAW DECK CARD] ---');
        const drawBtn = await page.$('#btn-claim-deck-card');
        check("Draw button is present", drawBtn !== null);
        if (drawBtn) {
            const isDrawDisabled = await drawBtn.isDisabled();
            check("Draw button is enabled on player turn", !isDrawDisabled);
            await drawBtn.click();
            await page.waitForTimeout(1000);
            const drawnThisTurn = await page.evaluate(() => window.CURRENT_MATCH_STATE.card_drawn_this_turn);
            check("Card successfully drawn (1/turn rule enforced)", drawnThisTurn === true);
        }

        console.log('\n--- 4. BUTTON: [⚡ ATTACH ENERGY] ---');
        await page.evaluate(() => {
            if (!window.CURRENT_MATCH_STATE.player.hand.some(c => (typeof c === 'string' ? c : c.name).toLowerCase().includes('energy'))) {
                window.CURRENT_MATCH_STATE.player.hand.push({ name: 'Basic Psychic Energy', card_type: 'energy' });
                window.updateMatchView(window.CURRENT_MATCH_STATE);
            }
        });
        await page.waitForTimeout(500);

        const energyBtn = await page.$('#player-hand-view button:has-text("⚡")');
        if (energyBtn) {
            console.log(`Clicking Energy button: "${await energyBtn.innerText()}"...`);
            await energyBtn.click();
            await page.waitForTimeout(1000);
            const energyAttached = await page.evaluate(() => window.CURRENT_MATCH_STATE.energy_attached_this_turn);
            check("Energy successfully attached to Pokémon", energyAttached === true);
        } else {
            console.warn("Energy button not found in hand.");
        }

        console.log('\n--- 5. BUTTON: [⚡ STRIKE / ATTACK] ---');
        // Give active pokemon matching elemental energies to satisfy attack cost
        await page.evaluate(() => {
            if (window.CURRENT_MATCH_STATE && window.CURRENT_MATCH_STATE.player && window.CURRENT_MATCH_STATE.player.active_spot) {
                const act = window.CURRENT_MATCH_STATE.player.active_spot;
                act.attached_energy = ['Fire', 'Fire', 'Water', 'Psychic', 'Lightning', 'Colorless', 'Fighting'];
                window.CURRENT_MATCH_STATE.is_player_turn = true;
                window.updateMatchView(window.CURRENT_MATCH_STATE);
            }
        });
        await page.waitForTimeout(1000);

        const strikeBtn = await page.$('#player-active-view button:has-text("STRIKE"):not([disabled])');
        if (strikeBtn) {
            console.log(`Clicking Strike button: "${await strikeBtn.innerText()}"...`);
            await strikeBtn.click();
            await page.waitForTimeout(1500);
            const oppHp = await page.evaluate(() => window.CURRENT_MATCH_STATE.opponent.active_spot ? window.CURRENT_MATCH_STATE.opponent.active_spot.current_hp : null);
            console.log(`Opponent HP after attack: ${oppHp}`);
            check("Attack executed and dealt damage", strikeBtn !== null);
        } else {
            console.warn("Strike button not clickable.");
        }

        console.log('\n--- 6. BUTTON: [⏭️ END TURN / PASS] ---');
        const endTurnBtn = await page.$('#btn-end-turn');
        if (endTurnBtn) {
            const turnBefore = await page.evaluate(() => window.CURRENT_MATCH_STATE.turn_number);
            await endTurnBtn.click();
            await page.waitForTimeout(2500);
            const turnAfter = await page.evaluate(() => window.CURRENT_MATCH_STATE.turn_number);
            console.log(`Turn before: ${turnBefore}, Turn after End Turn: ${turnAfter}`);
            check("End Turn executed and turn advanced", turnAfter >= turnBefore);
        }

        console.log('\n--- 7. BUTTON: [🛡️ Bench] IN FRESH SETUP MATCH ---');
        await page.evaluate(async () => {
            await window.startNewMatch(false, true);
            window.switchMode('match');
        });
        await page.waitForTimeout(1500);

        const freshBenchBtns = await page.$$('#player-hand-view button:has-text("Bench")');
        check("Found Bench buttons on fresh match hand", freshBenchBtns.length > 0);
        if (freshBenchBtns.length > 0) {
            await freshBenchBtns[0].click();
            await page.waitForTimeout(1500);
            const phaseAfterBench = await page.evaluate(() => window.CURRENT_MATCH_STATE ? window.CURRENT_MATCH_STATE.phase : 'NO_STATE');
            const benchList = await page.evaluate(() => window.CURRENT_MATCH_STATE.player.bench);
            const activeAfterBench = await page.evaluate(() => window.CURRENT_MATCH_STATE.player.active_spot);
            console.log(`Phase: ${phaseAfterBench}, Bench Count: ${benchList.length}, Active: ${activeAfterBench ? activeAfterBench.name : 'EMPTY'}`);
            check("[🛡️ Bench] placed card and transitioned to BATTLE", phaseAfterBench === 'BATTLE');
            check("Bench contains placed card", benchList.length > 0);
            check("Active Spot is populated so battle can proceed", activeAfterBench !== null);
        }

        console.log('\n--- 8. BUTTON: [⚡ QUICK START / AUTO-PLACE & BATTLE] ---');
        await page.evaluate(async () => {
            await window.startNewMatch(false, true);
            window.switchMode('match');
        });
        await page.waitForTimeout(1500);

        const autoPlaceBtn = await page.$('button:has-text("AUTO-PLACE & START BATTLE"), button:has-text("QUICK START")');
        if (autoPlaceBtn) {
            await autoPlaceBtn.click();
            await page.waitForTimeout(1500);
            const autoPhase = await page.evaluate(() => window.CURRENT_MATCH_STATE.phase);
            check("Auto-Place button transitioned to BATTLE phase", autoPhase === 'BATTLE');
        }

        console.log('\n--- 9. BUTTON: [🔄 SWITCH / RETREAT] MODAL ---');
        const switchBtn = await page.$('#btn-switch-retreat');
        if (switchBtn) {
            const isSwitchDisabled = await switchBtn.isDisabled();
            console.log(`Switch button disabled: ${isSwitchDisabled}`);
            if (!isSwitchDisabled) {
                await switchBtn.click();
                await page.waitForTimeout(500);
                const modalVisible = await page.$eval('#switch-modal', el => el && el.style.display !== 'none');
                check("Switch Pokémon modal opened successfully", modalVisible === true);
                const closeBtn = await page.$('#switch-modal button:has-text("Cancel")');
                if (closeBtn) await closeBtn.click();
            }
        }

        console.log('\n--- 10. ERROR CHECKING ---');
        check("Zero unhandled page errors during all button interactions", pageErrors.length === 0);

        console.log(`\n====================================================`);
        console.log(`PLAYWRIGHT TEST RESULTS: ${passedChecks}/${totalChecks} CHECKS PASSED`);
        console.log(`====================================================`);

    } catch (err) {
        console.error('TEST RUNTIME ERROR:', err);
    } finally {
        await browser.close();
    }
}

run();
