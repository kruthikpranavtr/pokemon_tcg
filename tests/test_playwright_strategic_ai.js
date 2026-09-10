const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SERVER_URL = 'http://127.0.0.1:8000';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runStrategicAiPlaywrightTest() {
    console.log('================================================================================');
    console.log('   POKEMON TCG STRATEGIC AI: HAND CARD POWERS & SEQUENTIAL STEP EXECUTION TEST');
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

        console.log('\n[Phase 2] Configuring hand with Trainer Powers (Potion, Energy, Basic)...');
        await page.evaluate(() => {
            CURRENT_MATCH_STATE.player.active_spot.current_hp = 40;
            CURRENT_MATCH_STATE.player.active_spot.max_hp = 70;
            CURRENT_MATCH_STATE.player.bench = [];
            CURRENT_MATCH_STATE.player.hand = ['Potion', 'Basic Fire Energy', 'Snorlax'];
            CURRENT_MATCH_STATE.energy_attached_this_turn = false;
            CURRENT_ROUTE_STEP_INDEX = 0;
            updateMatchView(CURRENT_MATCH_STATE);
        });

        const activeHpBefore = await page.evaluate(() => CURRENT_MATCH_STATE.player.active_spot.current_hp);
        const handBefore = await page.evaluate(() => CURRENT_MATCH_STATE.player.hand);
        console.log('  Active HP before: ' + activeHpBefore + '/70 HP');
        console.log('  Hand cards: ' + JSON.stringify(handBefore));

        // Wait for any initial fetch to finish
        await page.waitForFunction(() => {
            const btn = document.getElementById('btn-compute-winning-route');
            return btn && !btn.disabled && !btn.textContent.includes('COMPUTING');
        }, { timeout: 15000 });

        console.log('\n[Phase 3] Computing Winning Route on configured state...');
        await page.evaluate(async () => {
            await fetchStrategicAiAnalysis('BALANCED');
        });

        await page.waitForFunction(() => {
            const steps = document.querySelectorAll('#left-route-steps > div');
            return steps.length >= 3;
        }, { timeout: 15000 });

        const stepsCount = await page.locator('#left-route-steps > div').count();
        console.log('  Winning Route Steps count: ' + stepsCount);
        for (let i = 1; i <= stepsCount; i++) {
            const stepText = await page.locator('#left-route-steps > div:nth-child(' + i + ')').textContent();
            console.log('    Step ' + i + ': ' + stepText.replace(/\s+/g, ' ').trim());
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_hand_power_analyzed_steps.png') });
        console.log('  [Screenshot 12] Saved: 12_hand_power_analyzed_steps.png');

        const executeBtn = page.locator('#btn-execute-ai');

        // CLICK 1: Execute Step 1 (Potion Hand Item Power)
        console.log('\n[Phase 4] [CLICK 1] Executing Step 1 (Potion Hand Power)...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        const activeHpAfterStep1 = await page.evaluate(() => CURRENT_MATCH_STATE.player.active_spot.current_hp);
        const handAfterStep1 = await page.evaluate(() => CURRENT_MATCH_STATE.player.hand);
        const isStillPlayerTurn1 = await page.evaluate(() => CURRENT_MATCH_STATE.is_player_turn);
        console.log('  Active HP after Step 1 (healed): ' + activeHpAfterStep1 + '/70 HP');
        console.log('  Hand cards remaining: ' + JSON.stringify(handAfterStep1));
        console.log('  Is still Player turn: ' + isStillPlayerTurn1);

        if (activeHpAfterStep1 <= activeHpBefore) {
            throw new Error('Potion hand power should have healed active Pokémon HP!');
        }
        if (!isStillPlayerTurn1) {
            throw new Error('Step 1 must NOT end the player turn! Hand items execute before attack.');
        }

        const step1Status = await page.locator('#left-route-steps > div:nth-child(1)').textContent();
        const step2Status = await page.locator('#left-route-steps > div:nth-child(2)').textContent();
        console.log('  Step 1 Status: ' + step1Status.replace(/\s+/g, ' ').trim());
        console.log('  Step 2 Status: ' + step2Status.replace(/\s+/g, ' ').trim());
        if (!step1Status.includes('COMPLETED')) {
            throw new Error('Step 1 should be marked [COMPLETED ✅]');
        }
        if (!step2Status.includes('CURRENT STEP')) {
            throw new Error('Step 2 should be highlighted [CURRENT STEP ⚡]');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_step1_hand_power_executed.png') });
        console.log('  [Screenshot 13] Saved: 13_step1_hand_power_executed.png');

        // CLICK 2: Execute Step 2 (Bench Basic Snorlax)
        console.log('\n[Phase 5] [CLICK 2] Executing Step 2 (Bench Basic Pokémon)...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        const benchAfterStep2 = await page.evaluate(() => CURRENT_MATCH_STATE.player.bench.map(b => b.name));
        const isStillPlayerTurn2 = await page.evaluate(() => CURRENT_MATCH_STATE.is_player_turn);
        console.log('  Bench Pokémon after Step 2: ' + JSON.stringify(benchAfterStep2));
        console.log('  Is still Player turn: ' + isStillPlayerTurn2);
        if (!isStillPlayerTurn2) {
            throw new Error('Step 2 must NOT end the player turn!');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '14_step2_bench_executed.png') });
        console.log('  [Screenshot 14] Saved: 14_step2_bench_executed.png');

        // CLICK 3: Execute Step 3 (Attach Energy from Hand)
        console.log('\n[Phase 6] [CLICK 3] Executing Step 3 (Attach Energy 1/turn)...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        const energyBtnDisabled = await page.locator('#btn-add-energy-main').isDisabled();
        const energyBtnText = await page.locator('#btn-add-energy-main').textContent();
        console.log('  Energy button state: disabled=' + energyBtnDisabled + ', text="' + energyBtnText.trim() + '"');
        if (!energyBtnDisabled || !energyBtnText.includes('1/TURN USED')) {
            throw new Error('Energy button should be disabled with (1/TURN USED)!');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '15_step3_energy_attached.png') });
        console.log('  [Screenshot 15] Saved: 15_step3_energy_attached.png');

        // CLICK 4: Execute Step 4 (Offensive Strike)
        console.log('\n[Phase 7] [CLICK 4] Executing Step 4 (Offensive Strike)...');
        await executeBtn.click();
        await page.waitForTimeout(1000);

        const combatLogText = await page.locator('#combat-log').textContent();
        console.log('  Combat log after Strike attack:');
        const recentLogs = combatLogText.split('\n').filter(l => l.trim().length > 0).slice(-4);
        recentLogs.forEach(l => console.log('    ' + l.trim()));

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '16_step4_strike_executed.png') });
        console.log('  [Screenshot 16] Saved: 16_step4_strike_executed.png');

        console.log('\n================================================================================');
        console.log('  SUCCESS: HAND CARD POWERS & SEQUENTIAL STEP EXECUTION TESTS ALL PASSED!');
        console.log('================================================================================');

    } catch (err) {
        console.error('\nTEST FAILED:', err.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ERROR_hand_power_failure.png') });
        throw err;
    } finally {
        await browser.close();
    }
}

runStrategicAiPlaywrightTest().catch(e => {
    console.error(e);
    process.exit(1);
});
