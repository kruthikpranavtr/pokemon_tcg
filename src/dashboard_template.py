"""
Pokémon TCG Dashboard HTML/CSS/JS Template
Contains the complete dynamic frontend with:
- Cyberpunk / Esports TCG Arena UI
- Login & Account Creation modals
- User Collection state management with quantity badges
- Interactive 8-Card Booster Pack Opening with 3D flip-to-reveal animations
- '🎴 YOUR AVAILABLE CARDS' collection viewer with filters & search
- Owned-only 4-card battle selection and collection-based deck generation
- Preserved 60-card match simulator, AI recommendation engine, and opponent AI
- Backwards-compatible test tokens and handler signatures
"""

HTML_DASHBOARD_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POKÉMON TCG // DYNAMIC COLLECTION & BATTLE ENGINE</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-void: #03050c;
            --surface-cyber: rgba(8, 14, 28, 0.92);
            --surface-glass: rgba(13, 22, 44, 0.8);
            --neon-cyan: #00f3ff;
            --neon-cyan-glow: 0 0 15px rgba(0, 243, 255, 0.6), 0 0 30px rgba(0, 243, 255, 0.25);
            --neon-green: #00ff88;
            --neon-green-glow: 0 0 15px rgba(0, 255, 136, 0.6), 0 0 30px rgba(0, 255, 136, 0.25);
            --neon-magenta: #ff007f;
            --neon-magenta-glow: 0 0 15px rgba(255, 0, 127, 0.6), 0 0 30px rgba(255, 0, 127, 0.25);
            --neon-purple: #b026ff;
            --neon-amber: #ffaa00;
            --card-gold: #fbbf24;
            --text-glow: #e2f3fe;
            --text-dim: #738aa6;
            --font-orbitron: 'Orbitron', monospace;
            --font-mono: 'JetBrains Mono', monospace;
            --font-hud: 'Rajdhani', sans-serif;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: radial-gradient(circle at 50% 10%, #0c1427 0%, #060b17 60%, #020409 100%);
            color: #e2f3fe;
            font-family: var(--font-hud);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        .scanlines {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.15) 50%);
            background-size: 100% 4px;
            z-index: 1; pointer-events: none; opacity: 0.3;
        }

        .cyber-container {
            max-width: 1520px;
            margin: 0 auto;
            padding: 16px 20px 80px 20px;
            position: relative;
            z-index: 2;
        }

        header {
            text-align: center;
            margin-bottom: 16px;
            position: relative;
        }

        .cyber-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: var(--font-orbitron);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 2px;
            color: var(--neon-cyan);
            background: rgba(0, 243, 255, 0.08);
            border: 1px solid rgba(0, 243, 255, 0.4);
            padding: 5px 16px;
            border-radius: 30px;
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.2);
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .cyber-glitch-title {
            font-family: var(--font-orbitron);
            font-size: 2.1rem;
            font-weight: 900;
            color: #fff;
            letter-spacing: 2px;
            text-transform: uppercase;
            text-shadow: 0 0 20px rgba(0, 243, 255, 0.7), 0 0 40px rgba(0, 243, 255, 0.3);
            margin-bottom: 6px;
        }

        /* USER PROFILE & STATS BAR */
        .user-profile-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            background: rgba(13, 22, 44, 0.9);
            border: 1px solid rgba(0, 243, 255, 0.3);
            border-radius: 12px;
            padding: 10px 18px;
            margin-bottom: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
        }

        .user-greeting {
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: var(--font-orbitron);
            font-size: 0.95rem;
            font-weight: 800;
            color: #fff;
        }

        .user-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.5);
        }

        .collection-metrics-dock {
            display: flex;
            gap: 14px;
            align-items: center;
            flex-wrap: wrap;
        }

        .stat-pill {
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(2, 4, 9, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 5px 12px;
            border-radius: 6px;
            font-family: var(--font-mono);
            font-size: 0.8rem;
        }

        .stat-pill b {
            font-family: var(--font-orbitron);
            font-size: 0.95rem;
        }

        /* TOP TAB NAVIGATION BAR */
        .tab-nav-bar {
            display: flex;
            gap: 10px;
            justify-content: center;
            align-items: center;
            margin: 0 0 20px 0;
            background: rgba(13, 22, 44, 0.85);
            border: 1px solid rgba(0, 243, 255, 0.35);
            border-radius: 12px;
            padding: 8px 12px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(16px);
            flex-wrap: wrap;
        }

        .tab-btn {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 28, 0.95) 100%);
            border: 1px solid rgba(0, 243, 255, 0.2);
            color: var(--text-dim);
            font-family: var(--font-orbitron);
            font-size: 0.82rem;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .tab-btn:hover {
            color: #fff;
            border-color: var(--neon-cyan);
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.3);
        }

        .tab-btn.active {
            background: linear-gradient(135deg, rgba(0, 243, 255, 0.25) 0%, rgba(176, 38, 255, 0.25) 100%);
            border-color: var(--neon-cyan);
            color: #fff;
            box-shadow: 0 0 16px rgba(0, 243, 255, 0.45);
        }

        /* BUTTONS */
        .btn-action-main {
            background: linear-gradient(135deg, rgba(0, 243, 255, 0.2) 0%, rgba(0, 255, 136, 0.2) 100%);
            border: 1px solid var(--neon-cyan);
            color: #fff;
            font-family: var(--font-orbitron);
            font-weight: 800;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            text-shadow: 0 0 8px rgba(0, 243, 255, 0.5);
        }
        .btn-action-main:hover {
            box-shadow: var(--neon-cyan-glow);
            transform: translateY(-1px);
        }

        .btn-cyber-sm {
            background: rgba(13, 22, 44, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #e2f3fe;
            font-family: var(--font-orbitron);
            font-size: 0.72rem;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .btn-cyber-sm:hover {
            border-color: var(--neon-cyan);
            color: #fff;
        }

        /* ================= OPEN PACK VIEW ================= */
        .pack-open-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 30px 10px;
        }

        .pack-hero-stage {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 24px;
        }

        .booster-pack-box {
            width: 220px;
            height: 310px;
            background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 40%, #311042 100%);
            border: 3px solid var(--neon-cyan);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 0 35px rgba(0, 243, 255, 0.4), inset 0 0 25px rgba(255, 0, 127, 0.2);
            cursor: pointer;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
            animation: packFloat 3s ease-in-out infinite alternate;
        }
        .booster-pack-box:hover {
            transform: scale(1.05) rotate(1deg);
            box-shadow: 0 0 50px rgba(0, 243, 255, 0.7), inset 0 0 35px rgba(255, 0, 127, 0.4);
        }

        @keyframes packFloat {
            0% { transform: translateY(0px); }
            100% { transform: translateY(-8px); }
        }

        .pack-shimmer {
            position: absolute;
            top: -100%; left: -100%; width: 300%; height: 300%;
            background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.15) 50%, transparent 60%);
            animation: packShimmer 4s infinite;
            pointer-events: none;
        }
        @keyframes packShimmer {
            0% { transform: translateY(-30%); }
            100% { transform: translateY(30%); }
        }

        .pack-reveal-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            width: 100%;
            max-width: 1200px;
            margin-top: 20px;
        }
        @media (max-width: 900px) {
            .pack-reveal-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 500px) {
            .pack-reveal-grid { grid-template-columns: 1fr; }
        }

        /* 3D FLIP CARD EFFECT */
        .card-flip-wrapper {
            perspective: 1000px;
            height: 320px;
            cursor: pointer;
        }
        .card-flip-inner {
            position: relative;
            width: 100%;
            height: 100%;
            text-align: center;
            transition: transform 0.7s cubic-bezier(0.4, 0, 0.2, 1);
            transform-style: preserve-3d;
        }
        .card-flip-wrapper.flipped .card-flip-inner {
            transform: rotateY(180deg);
        }

        .card-face {
            position: absolute;
            width: 100%;
            height: 100%;
            -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
            border-radius: 12px;
            overflow: hidden;
        }

        .card-face-back {
            background: radial-gradient(circle at 50% 50%, #1e1e38 0%, #0b0f1e 100%);
            border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 20px rgba(0, 243, 255, 0.35);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 14px;
        }

        .card-face-front {
            background: #0d162c;
            border: 2px solid rgba(255, 255, 255, 0.15);
            transform: rotateY(180deg);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 10px;
            text-align: left;
        }

        /* Rarity Borders */
        .rarity-common { border-color: #94a3b8; box-shadow: 0 0 15px rgba(148, 163, 184, 0.3); }
        .rarity-uncommon { border-color: #34d399; box-shadow: 0 0 18px rgba(52, 211, 153, 0.45); }
        .rarity-rare { border-color: #38bdf8; box-shadow: 0 0 22px rgba(56, 189, 248, 0.55); }
        .rarity-ultra-rare { border-color: #fbbf24; box-shadow: 0 0 30px rgba(251, 191, 36, 0.7); }
        .rarity-special { border-color: #f43f5e; box-shadow: 0 0 35px rgba(244, 63, 94, 0.8), 0 0 15px rgba(168, 85, 247, 0.5); }

        /* ================= YOUR AVAILABLE CARDS ================= */
        .all-cards-section {
            background: var(--surface-cyber);
            border: 1px solid rgba(0, 243, 255, 0.3);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
        }

        .deck-builder-control-card {
            background: rgba(13, 22, 44, 0.85);
            border: 1px solid rgba(0, 243, 255, 0.25);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 16px;
        }

        .cards-filter-bar {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 20px;
            background: rgba(2, 4, 9, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 14px;
        }

        .cards-search-input {
            width: 100%;
            background: rgba(13, 22, 44, 0.85);
            border: 1px solid rgba(0, 243, 255, 0.35);
            border-radius: 6px;
            padding: 10px 14px;
            color: #fff;
            font-family: var(--font-hud);
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        .cards-search-input:focus {
            border-color: var(--neon-cyan);
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.4);
        }

        .filter-chip-row {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            align-items: center;
        }

        .filter-chip-row-label {
            font-family: var(--font-orbitron);
            font-size: 0.72rem;
            color: var(--text-dim);
            margin-right: 4px;
        }

        .filter-chip {
            background: rgba(13, 22, 44, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-dim);
            font-family: var(--font-mono);
            font-size: 0.72rem;
            padding: 5px 12px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .filter-chip:hover {
            color: #fff;
            border-color: var(--neon-cyan);
        }
        .filter-chip.active {
            background: rgba(0, 243, 255, 0.2);
            border-color: var(--neon-cyan);
            color: #fff;
            font-weight: 700;
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.3);
        }

        .all-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 14px;
        }

        .owned-card-box {
            background: rgba(13, 22, 44, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            position: relative;
        }
        .owned-card-box:hover {
            transform: translateY(-2px);
            border-color: var(--neon-cyan);
            box-shadow: 0 0 18px rgba(0, 243, 255, 0.25);
        }

        .qty-badge {
            position: absolute;
            top: 8px;
            right: 8px;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: #000;
            font-family: var(--font-orbitron);
            font-weight: 900;
            font-size: 0.8rem;
            padding: 3px 8px;
            border-radius: 12px;
            box-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
            z-index: 2;
        }

        /* 4 Slots Display */
        .slots-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin-top: 14px;
        }

        /* 3-COLUMN MATCH ARENA */
        .app-3col-layout {
            display: grid;
            grid-template-columns: 280px 1fr 300px;
            gap: 18px;
        }
        @media (max-width: 1200px) {
            .app-3col-layout { grid-template-columns: 1fr; }
        }

        .side-column-panel {
            background: var(--surface-cyber);
            border: 1px solid rgba(0, 243, 255, 0.3);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            max-height: 940px;
            overflow-y: auto;
        }
        .side-column-panel::-webkit-scrollbar {
            width: 5px;
        }
        .side-column-panel::-webkit-scrollbar-track {
            background: rgba(2, 4, 9, 0.6);
        }
        .side-column-panel::-webkit-scrollbar-thumb {
            background: rgba(0, 243, 255, 0.3);
            border-radius: 3px;
        }
        .side-column-panel::-webkit-scrollbar-thumb:hover {
            background: var(--neon-cyan);
        }


        .tcg-playmat-container {
            background: rgba(6, 11, 23, 0.95);
            border: 2px solid rgba(0, 243, 255, 0.4);
            border-radius: 14px;
            padding: 16px;
            box-shadow: 0 0 35px rgba(0, 0, 0, 0.9), inset 0 0 40px rgba(0, 243, 255, 0.05);
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .section-label {
            font-family: var(--font-orbitron);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 1px;
            color: var(--text-dim);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .bench-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }

        .active-spot-center {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .visual-active-card {
            width: 100%;
            max-width: 480px;
            background: linear-gradient(135deg, rgba(13, 22, 44, 0.95) 0%, rgba(5, 10, 20, 0.95) 100%);
            border: 2px solid var(--neon-cyan);
            border-radius: 12px;
            padding: 14px;
            box-shadow: 0 0 25px rgba(0, 243, 255, 0.35);
        }
        .opp-active-card {
            border-color: var(--neon-magenta);
            box-shadow: 0 0 25px rgba(255, 0, 127, 0.35);
        }

        .arena-divider-bar {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 4px 0;
        }
        .divider-line {
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0, 243, 255, 0.4), transparent);
        }
        .divider-badge {
            font-family: var(--font-orbitron);
            font-size: 0.65rem;
            letter-spacing: 2px;
            color: var(--neon-cyan);
        }

        .hand-grid {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            min-height: 50px;
            align-items: center;
        }

        .match-actions-bar {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .combat-log-box {
            background: rgba(2, 4, 9, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 10px;
            font-family: var(--font-mono);
            font-size: 0.72rem;
            line-height: 1.4;
            color: #cbd5e1;
            height: 200px;
            overflow-y: auto;
        }

        /* FACE-DOWN DECK PILES (RUMMY/TCG DRAW PILE) */
        .face-down-deck-box {
            width: 100px;
            height: 140px;
            background: radial-gradient(circle at 50% 50%, #1e293b 0%, #090e1a 100%);
            border: 2px solid var(--neon-cyan);
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 243, 255, 0.3), inset 0 0 10px rgba(0, 243, 255, 0.2);
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            user-select: none;
            cursor: pointer;
        }
        .face-down-deck-box:hover:not(.deck-disabled) {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0, 243, 255, 0.5), inset 0 0 15px rgba(0, 243, 255, 0.35);
            border-color: #38bdf8;
        }
        .face-down-deck-box.opp-deck {
            border-color: var(--neon-magenta);
            box-shadow: 0 4px 15px rgba(255, 0, 127, 0.3), inset 0 0 10px rgba(255, 0, 127, 0.2);
            cursor: not-allowed;
            pointer-events: none !important;
        }
        .face-down-deck-box.deck-disabled {
            opacity: 0.55;
            cursor: not-allowed;
            filter: grayscale(0.5);
        }
        .deck-card-back-pattern {
            width: 76px;
            height: 104px;
            border: 1px dashed rgba(255, 255, 255, 0.25);
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(2, 6, 23, 0.95));
            pointer-events: none;
        }
        .deck-pokeball-icon {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            border: 2px solid rgba(255, 255, 255, 0.6);
            background: linear-gradient(180deg, #ef4444 50%, #f8fafc 50%);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
            position: relative;
        }
        .deck-pokeball-center {
            width: 12px;
            height: 12px;
            background: #fff;
            border: 2px solid #0f172a;
            border-radius: 50%;
            box-shadow: 0 0 4px rgba(0,0,0,0.8);
        }
        .deck-counter-badge {
            margin-top: 6px;
            font-family: var(--font-orbitron);
            font-size: 0.72rem;
            font-weight: 900;
            color: #fff;
            text-shadow: 0 0 6px rgba(0, 243, 255, 0.8);
        }

        /* MODALS */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(12px);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .modal-card {
            background: linear-gradient(135deg, #0d162c, #060b17);
            border: 2px solid var(--neon-cyan);
            border-radius: 14px;
            padding: 24px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 0 40px rgba(0, 243, 255, 0.5);
        }

        .neon-input {
            width: 100%;
            background: rgba(2, 4, 9, 0.8);
            border: 1px solid rgba(0, 243, 255, 0.35);
            border-radius: 6px;
            padding: 10px 14px;
            color: #fff;
            font-family: var(--font-mono);
            font-size: 0.88rem;
            outline: none;
            margin-top: 6px;
            margin-bottom: 12px;
        }
        .neon-input:focus {
            border-color: var(--neon-cyan);
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.4);
        }
    </style>
</head>
<body>
    <div class="scanlines"></div>

    <div class="cyber-container">
        <!-- HEADER -->
        <header>
            <div class="cyber-badge">🏆 OFFICIAL POKÉMON TCG ESPORTS MATCH ARENA // VER 2.2</div>
            <h1 class="cyber-glitch-title">POKÉMON TCG // COMPETITIVE MATCH ENGINE</h1>
        </header>

        <!-- USER PROFILE & LIVE COLLECTION STATS DOCK -->
        <div id="user-profile-bar" class="user-profile-bar" style="display:none;">
            <div class="user-greeting">
                <div class="user-avatar" id="header-user-avatar">👤</div>
                <div>
                    <div>Welcome, <span id="header-username" style="color:var(--neon-cyan);">Trainer</span>!</div>
                    <div style="font-size:0.68rem; color:var(--text-dim); font-family:var(--font-mono);">Logged in • Ready for Battle</div>
                </div>
            </div>
            <div class="collection-metrics-dock">
                <div class="stat-pill" style="border-color:var(--neon-cyan);">
                    <span>🎴 Total Cards:</span>
                    <b id="stat-total-cards" style="color:var(--neon-cyan);">0</b>
                </div>
                <div class="stat-pill" style="border-color:#ef4444;">
                    <span>🐉 Pokémon:</span>
                    <b id="stat-pokemon-cards" style="color:#f87171;">0</b>
                </div>
                <div class="stat-pill" style="border-color:var(--neon-amber);">
                    <span>🧰 Trainer:</span>
                    <b id="stat-trainer-cards" style="color:#fbbf24;">0</b>
                </div>
                <div class="stat-pill" style="border-color:var(--neon-green);">
                    <span>⚡ Energy:</span>
                    <b id="stat-energy-cards" style="color:#34d399;">0</b>
                </div>
                <button class="btn-cyber-sm" style="border-color:#ef4444; color:#fca5a5;" onclick="handleLogout()">🚪 Logout</button>
            </div>
        </div>

        <!-- AUTH BAR (WHEN LOGGED OUT) -->
        <div id="logged-out-banner" class="user-profile-bar" style="justify-content:center; gap:20px;">
            <span style="font-family:var(--font-orbitron); font-size:0.9rem; color:#fff;">Welcome to Pokémon TCG! Please log in to manage your collection and battle:</span>
            <div style="display:flex; gap:10px;">
                <button class="btn-action-main" style="padding:8px 18px; font-size:0.8rem;" onclick="showAuthModal('login')">🔑 LOGIN</button>
                <button class="btn-cyber-sm" style="padding:8px 18px; font-size:0.8rem; border-color:var(--neon-green); color:var(--neon-green);" onclick="showAuthModal('register')">📝 CREATE ACCOUNT</button>
            </div>
        </div>

        <!-- MODE SWITCH TABS -->
        <div class="tab-nav-bar">
            <button id="tab-btn-pack" class="tab-btn" onclick="switchMode('pack')">🎁 OPEN CARD PACK</button>
            <button id="tab-btn-cards" class="tab-btn" onclick="switchMode('cards')">🎴 YOUR AVAILABLE CARDS</button>
            <button id="tab-btn-match" class="tab-btn active" onclick="switchMode('match')">⚔️ 60-CARD LIVE MATCH</button>
            <button id="tab-btn-deck" class="tab-btn" onclick="switchMode('deck')">🏆 PRE-SET META ARCHETYPES</button>
            <button id="tab-btn-history" class="tab-btn" onclick="switchMode('history')">📜 PACK HISTORY</button>
        </div>

        <!-- ================= VIEW 1: OPEN CARD PACK ================= -->
        <div id="view-pack" style="display:none;">
            <div class="pack-open-container">
                <div class="pack-hero-stage">
                    <div style="font-family:var(--font-orbitron); font-size:1.4rem; font-weight:900; color:var(--neon-cyan); margin-bottom:8px; text-shadow:0 0 15px rgba(0,243,255,0.6);">
                        🎁 OFFICIAL 8-CARD BOOSTER PACK
                    </div>
                    <div style="font-size:0.85rem; color:var(--text-dim); margin-bottom:18px;">
                        Guaranteed: <b>5 Pokémon Cards</b> + <b>3 Trainer/Energy Cards</b> &bull; Duplicates Allowed (~40% owned probability)
                    </div>

                    <div class="booster-pack-box" onclick="openBoosterPack()">
                        <div class="pack-shimmer"></div>
                        <div style="font-size:0.75rem; color:var(--neon-cyan); font-family:var(--font-orbitron); font-weight:800; letter-spacing:1px;">BOOSTER PACK</div>
                        <div style="text-align:center;">
                            <div style="font-size:3.5rem; margin-bottom:4px;">📦</div>
                            <div style="font-family:var(--font-orbitron); font-size:1.1rem; font-weight:900; color:#fff;">POKÉMON TCG</div>
                            <div style="font-size:0.75rem; color:var(--neon-amber); font-weight:800;">8 CARDS EXPANSION</div>
                        </div>
                        <button id="btn-open-pack" class="btn-action-main" style="width:100%; padding:10px; font-size:0.85rem;" onclick="event.stopPropagation(); openBoosterPack()">
                            ✨ OPEN PACK
                        </button>
                    </div>
                </div>

                <!-- Pack Reveal Area -->
                <div id="pack-reveal-area" style="display:none; width:100%; flex-direction:column; align-items:center;">
                    <div style="display:flex; justify-content:space-between; align-items:center; width:100%; max-width:1200px; margin-bottom:10px; flex-wrap:wrap; gap:10px;">
                        <div style="font-family:var(--font-orbitron); font-size:1.1rem; color:var(--neon-green); font-weight:800;">
                            🎴 CLICK EACH CARD TO REVEAL (<span id="revealed-count">0</span>/8 REVEALED)
                        </div>
                        <button class="btn-cyber-sm" style="background:rgba(0,243,255,0.15); border-color:var(--neon-cyan); color:var(--neon-cyan);" onclick="revealAllPackCards()">
                            ⚡ REVEAL ALL CARDS
                        </button>
                    </div>
                    <div id="pack-cards-grid" class="pack-reveal-grid"></div>

                    <!-- Post-Reveal Summary Banner -->
                    <div id="pack-summary-dock" style="display:none; width:100%; max-width:1200px; margin-top:24px; background:rgba(13,22,44,0.9); border:2px solid var(--neon-green); border-radius:12px; padding:20px; text-align:center; box-shadow:0 0 30px rgba(0,255,136,0.3);">
                        <div style="font-family:var(--font-orbitron); font-size:1.3rem; color:var(--neon-green); font-weight:900; margin-bottom:8px;">
                            🎉 PACK OPENED SUCCESSFULLY!
                        </div>
                        <div style="font-size:0.85rem; color:#cbd5e1; margin-bottom:16px;">
                            All 8 cards have been added to your collection! Check "Your Available Cards" to build your battle deck.
                        </div>
                        <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
                            <button class="btn-action-main" style="padding:10px 22px; font-size:0.85rem;" onclick="openBoosterPack()">
                                🎁 OPEN ANOTHER PACK
                            </button>
                            <button class="btn-cyber-sm" style="padding:10px 22px; font-size:0.85rem; border-color:var(--neon-cyan); color:var(--neon-cyan);" onclick="switchMode('cards')">
                                🎴 VIEW YOUR AVAILABLE CARDS
                            </button>
                            <button class="btn-cyber-sm" style="padding:10px 22px; font-size:0.85rem; border-color:var(--neon-green); color:var(--neon-green);" onclick="switchMode('match')">
                                ⚔️ PLAY MATCH ARENA
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ================= VIEW 2: 🎴 YOUR AVAILABLE CARDS ================= -->
        <div id="view-cards" class="all-cards-section" style="display:none;">
            <!-- EMPTY DECK GUIDANCE BANNER -->
            <div id="empty-deck-alert-banner" style="display:none; margin-bottom:16px; background:linear-gradient(135deg, rgba(239,68,68,0.18), rgba(245,158,11,0.18)); border:2px solid var(--neon-amber); border-radius:10px; padding:16px 20px; box-shadow:0 0 25px rgba(245,158,11,0.35);">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-family:var(--font-orbitron); font-size:1.1rem; font-weight:900; color:var(--neon-amber); display:flex; align-items:center; gap:8px;">
                            ⚠️ YOUR BATTLE DECK IS EMPTY!
                        </div>
                        <div style="font-size:0.85rem; color:#cbd5e1; margin-top:4px;">
                            Add cards from your collection below or click <b>Quick Auto-Fill</b> to assemble 60 cards, then click <b>Save & Start Battle</b> to begin!
                        </div>
                    </div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <button class="btn-action-main" style="padding:8px 18px; font-size:0.8rem; background:linear-gradient(135deg, #f59e0b, #eab308); color:#000; font-weight:900; border:none; box-shadow:0 0 15px rgba(245,158,11,0.4);" onclick="quickAutoFillAndStartBattle()">
                            ⚡ QUICK AUTO-FILL & START BATTLE
                        </button>
                        <button class="btn-action-main" style="padding:8px 18px; font-size:0.8rem; background:linear-gradient(135deg, #00f3ff, #00ff88); color:#000; font-weight:900; border:none; box-shadow:0 0 15px rgba(0,255,136,0.4);" onclick="saveAndStartBattle()">
                            ⚔️ SAVE & START BATTLE
                        </button>
                    </div>
                </div>
            </div>

            <!-- 3-SLOT 60-CARD DECK BUILDER DOCK -->
            <div class="deck-builder-control-card" style="border: 2px solid var(--neon-cyan); box-shadow: 0 0 25px rgba(0,243,255,0.25); margin-bottom: 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:14px;">
                    <div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div style="font-family:var(--font-orbitron); font-size:1.15rem; font-weight:900; color:var(--neon-cyan);">
                                🎴 60-CARD DECK BUILDER
                            </div>
                            <span id="active-deck-badge" class="cyber-badge" style="font-size:0.65rem; border-color:var(--neon-green); color:var(--neon-green);">ACTIVE FOR BATTLE</span>
                        </div>
                        <div style="font-size:0.82rem; color:var(--text-dim); margin-top:2px;">
                            Build up to 3 custom 60-card decks from your collection. Add Pokémon, Trainers, and Energy. Select a deck for 60-Card Live Matches!
                        </div>
                    </div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <button id="btn-save-start-battle" class="btn-action-main" style="padding:8px 18px; font-size:0.8rem; background:linear-gradient(135deg, #00f3ff, #00ff88); color:#000; font-weight:900; border:none; box-shadow:0 0 15px rgba(0,255,136,0.4);" onclick="saveAndStartBattle()">
                            ⚔️ SAVE & START BATTLE
                        </button>
                        <button id="btn-save-deck" class="btn-action-main" style="padding:8px 16px; font-size:0.8rem; border-color:var(--neon-cyan);" onclick="saveCurrentDeckSlot()">
                            💾 SAVE DECK
                        </button>
                        <button id="btn-select-battle-deck" class="btn-action-main" style="padding:8px 16px; font-size:0.8rem; border-color:var(--neon-green); box-shadow:var(--neon-green-glow);" onclick="selectCurrentDeckForBattle()">
                            ⚔️ SELECT FOR BATTLE
                        </button>
                        <button id="btn-take-to-battle" class="btn-action-main" style="padding:8px 18px; font-size:0.8rem; background:linear-gradient(135deg, #00f3ff, #00ff88); color:#000; font-weight:900; border:none; box-shadow:0 0 15px rgba(0,255,136,0.4);" onclick="startBattleWithCurrentDeck()">
                            ⚔️ TAKE TO BATTLE
                        </button>
                        <button class="btn-cyber-sm" style="background:linear-gradient(135deg, #f59e0b, #eab308); color:#000; font-weight:900; padding:8px 12px; font-size:0.75rem; border:none; box-shadow:0 0 10px rgba(245,158,11,0.3);" onclick="autoCompleteBalancedDeck()" title="Automatically balance your deck with Pokémon, Trainers, and matching Energies to reach 60 cards">
                            ⚡ AUTO-COMPLETE DECK (60)
                        </button>
                        <button class="btn-cyber-sm" style="border-color:#ef4444; color:#fca5a5; padding:8px 12px; font-size:0.75rem;" onclick="clearCurrentDeck()">
                            🗑️ CLEAR
                        </button>
                    </div>
                </div>

                <!-- Deck Tabs (Slot 1, Slot 2, Slot 3) -->
                <div style="display:flex; gap:8px; align-items:center; margin-bottom:12px; border-bottom:1px solid rgba(0,243,255,0.2); padding-bottom:8px;">
                    <button id="deck-tab-1" class="tab-btn active" style="padding:6px 14px; font-size:0.78rem;" onclick="switchDeckSlot(1)">My Deck 1 (<span id="deck-count-tab-1">0</span>/60)</button>
                    <button id="deck-tab-2" class="tab-btn" style="padding:6px 14px; font-size:0.78rem;" onclick="switchDeckSlot(2)">My Deck 2 (<span id="deck-count-tab-2">0</span>/60)</button>
                    <button id="deck-tab-3" class="tab-btn" style="padding:6px 14px; font-size:0.78rem;" onclick="switchDeckSlot(3)">My Deck 3 (<span id="deck-count-tab-3">0</span>/60)</button>
                    <div style="margin-left:auto; display:flex; align-items:center; gap:8px;">
                        <input type="text" id="deck-name-input" class="neon-input" style="padding:5px 10px; font-size:0.78rem; width:180px; margin:0;" placeholder="Deck Name" value="My Deck 1" onchange="updateCurrentDeckName(this.value)">
                        <span id="deck-total-count-badge" class="cyber-badge" style="font-size:0.75rem; padding:4px 10px;">Cards: <b id="deck-cards-count" style="color:#fff;">0</b> / 60</span>
                    </div>
                </div>

                <!-- Deck Card Tray (chips of cards in current deck) -->
                <div id="deck-cards-tray" style="display:flex; flex-wrap:wrap; gap:6px; min-height:48px; max-height:160px; overflow-y:auto; background:rgba(2,4,9,0.7); border:1px solid rgba(0,243,255,0.15); border-radius:6px; padding:8px;">
                    <div style="color:var(--text-dim); font-size:0.75rem; font-style:italic; width:100%; text-align:center; padding:10px 0;">This deck is empty. Click "+ ADD TO DECK" on any card below to add up to 60 cards.</div>
                </div>
            </div>

            <!-- SEARCH & FILTER TOOLBAR -->
            <div class="cards-filter-bar">
                <input type="text" id="cards-search-input" class="cards-search-input" placeholder="🔍 Search your cards by name, attack, ability, or type..." oninput="debounceFilterOwnedCards()">

                <!-- Category Filters -->
                <div class="filter-chip-row">
                    <span class="filter-chip-row-label">CATEGORY:</span>
                    <button class="filter-chip active" data-filter-cat="all" onclick="setCategoryFilter('all', this)">ALL CARDS</button>
                    <button class="filter-chip" data-filter-cat="pokemon" onclick="setCategoryFilter('pokemon', this)">🐉 POKÉMON</button>
                    <button class="filter-chip" data-filter-cat="trainer" onclick="setCategoryFilter('trainer', this)">🧰 TRAINER</button>
                    <button class="filter-chip" data-filter-cat="item" onclick="setCategoryFilter('item', this)">💊 ITEM</button>
                    <button class="filter-chip" data-filter-cat="supporter" onclick="setCategoryFilter('supporter', this)">👤 SUPPORTER</button>
                    <button class="filter-chip" data-filter-cat="stadium" onclick="setCategoryFilter('stadium', this)">🏟️ STADIUM</button>
                    <button class="filter-chip" data-filter-cat="energy" onclick="setCategoryFilter('energy', this)">⚡ ENERGY</button>
                </div>

                <!-- Stage Filters -->
                <div class="filter-chip-row">
                    <span class="filter-chip-row-label">STAGE:</span>
                    <button class="filter-chip active" data-filter-stage="all" onclick="setStageFilter('all', this)">ALL STAGES</button>
                    <button class="filter-chip" data-filter-stage="basic" onclick="setStageFilter('basic', this)">🟢 BASIC POKÉMON</button>
                    <button class="filter-chip" data-filter-stage="stage 1" onclick="setStageFilter('stage 1', this)">🧬 STAGE 1</button>
                    <button class="filter-chip" data-filter-stage="stage 2" onclick="setStageFilter('stage 2', this)">🧬 STAGE 2</button>
                </div>

                <!-- Rarity Filters -->
                <div class="filter-chip-row">
                    <span class="filter-chip-row-label">RARITY:</span>
                    <button class="filter-chip active" data-filter-rarity="all" onclick="setRarityFilter('all', this)">ALL RARITIES</button>
                    <button class="filter-chip" data-filter-rarity="Common" onclick="setRarityFilter('Common', this)">⚪ COMMON</button>
                    <button class="filter-chip" data-filter-rarity="Uncommon" onclick="setRarityFilter('Uncommon', this)">🟢 UNCOMMON</button>
                    <button class="filter-chip" data-filter-rarity="Rare" onclick="setRarityFilter('Rare', this)">🔵 RARE</button>
                    <button class="filter-chip" data-filter-rarity="Ultra Rare" onclick="setRarityFilter('Ultra Rare', this)">🟡 ULTRA RARE</button>
                    <button class="filter-chip" data-filter-rarity="Special" onclick="setRarityFilter('Special', this)">🔴 SPECIAL / LEGENDARY</button>
                </div>
            </div>

            <!-- EMPTY COLLECTION PROMPT -->
            <div id="empty-collection-box" style="display:none; text-align:center; padding:40px 20px; background:rgba(2,4,9,0.7); border:1px dashed rgba(0,243,255,0.3); border-radius:10px;">
                <div style="font-size:3rem; margin-bottom:8px;">📦</div>
                <div style="font-family:var(--font-orbitron); font-size:1.1rem; color:#fff; font-weight:800; margin-bottom:6px;">Your collection is currently empty!</div>
                <div style="font-size:0.85rem; color:var(--text-dim); margin-bottom:18px;">Open card packs in the "Open Card Pack" section to start collecting Pokémon, Trainer, and Energy cards!</div>
                <button class="btn-action-main" style="padding:10px 24px; font-size:0.85rem;" onclick="switchMode('pack')">🎁 OPEN YOUR FIRST PACK</button>
            </div>

            <!-- OWNED CARDS GRID -->
            <div id="owned-cards-grid" class="all-cards-grid"></div>
        </div>

        <!-- ================= VIEW 3: 60-CARD LIVE MATCH ================= -->
        <div id="view-match">
            <div class="app-3col-layout">
                <!-- LEFT COLUMN: AI RECOMMENDATION SYSTEM -->
                <div class="side-column-panel">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div class="section-label" style="color:var(--neon-cyan); margin-bottom:0;"><span>🧠 AI STRATEGIC ENGINE</span></div>
                        <span id="left-engine-badge" class="cyber-badge" style="font-size:0.6rem; padding:2px 6px;">POMDP MCTS</span>
                    </div>

                    <!-- WIN RATE & CONFIDENCE INTERVAL -->
                    <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(0,243,255,0.2); border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-size:0.7rem; color:var(--text-dim); font-family:var(--font-orbitron);">LIVE MATCH WIN RATE</div>
                        <div id="left-win-pct" style="font-family:var(--font-orbitron); font-size:1.8rem; font-weight:900; color:var(--neon-cyan);">--%</div>
                        <div id="left-confidence-interval" style="font-size:0.68rem; color:#94a3b8; font-family:var(--font-mono); margin-top:2px;">95% CI: [--%, --%] &bull; 100 Sims</div>
                    </div>
                    
                    <!-- TOP RECOMMENDED ACTION -->
                    <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:10px;">
                        <div style="font-family:var(--font-orbitron); font-size:0.7rem; color:var(--neon-cyan); margin-bottom:4px;">TOP RECOMMENDED ACTION</div>
                        <div id="left-rec-action" style="font-family:var(--font-orbitron); font-size:0.88rem; font-weight:800; color:#fff;">Evaluating Match State...</div>
                        <div id="left-rec-desc" style="font-size:0.78rem; color:#cbd5e1; margin-top:4px; line-height:1.3;">AI Engine computes real-time optimal plays from the arena...</div>
                    </div>

                    <!-- THE WINNING ROUTE ROADMAP -->
                    <div id="left-winning-route-box" style="background:rgba(0,243,255,0.04); border:1px solid rgba(0,243,255,0.3); border-radius:8px; padding:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <div style="font-family:var(--font-orbitron); font-size:0.72rem; color:var(--neon-cyan); font-weight:800;">🎯 THE WINNING ROUTE</div>
                            <span id="left-route-turns" class="cyber-badge" style="font-size:0.62rem; padding:1px 6px; border-color:var(--neon-green); color:var(--neon-green);">3 TURNS</span>
                        </div>
                        <div id="left-route-summary" style="font-size:0.75rem; color:#e2f3fe; margin-bottom:8px; font-weight:600;">Mapping optimal prize extraction sequence...</div>
                        <div id="left-route-steps" style="display:flex; flex-direction:column; gap:6px; font-size:0.72rem;">
                            <!-- Steps rendered dynamically -->
                        </div>
                        <div id="left-route-condition" style="margin-top:8px; font-size:0.68rem; color:#fbbf24; font-family:var(--font-mono); border-top:1px dashed rgba(255,255,255,0.1); padding-top:6px;">
                            💡 Key: Maintain energy tempo and protect bench attackers.
                        </div>
                    </div>

                    <!-- TOP RANKED PLAYS WITH DELTAS -->
                    <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:10px;">
                        <div style="font-family:var(--font-orbitron); font-size:0.7rem; color:var(--neon-amber); margin-bottom:4px;">TOP RANKED PLAYS &bull; Δ%</div>
                        <div id="left-ranked-list" style="font-size:0.75rem; display:flex; flex-direction:column; gap:4px;">
                            <div>1. Calculating optimal play...</div>
                            <div>2. Evaluating counter-attacks...</div>
                            <div>3. Analyzing energy tempo...</div>
                        </div>
                    </div>

                    <!-- PREDICTED OPPONENT COUNTER & RESPONSE -->
                    <div id="left-opponent-responses-box" style="background:rgba(255,0,127,0.04); border:1px solid rgba(255,0,127,0.25); border-radius:8px; padding:10px;">
                        <div style="font-family:var(--font-orbitron); font-size:0.7rem; color:var(--neon-magenta); margin-bottom:4px;">🔮 PREDICTED OPPONENT COUNTER</div>
                        <div id="left-opp-dangerous" style="font-size:0.75rem; color:#fca5a5; font-weight:700;">Anticipating opponent counter-offensive...</div>
                        <div id="left-opp-counter" style="font-size:0.72rem; color:#cbd5e1; margin-top:4px; line-height:1.3;">Counter-strategy: Preserve bench reserve security.</div>
                    </div>

                    <!-- MATHEMATICAL FORMULA & EXPECTED VALUE -->
                    <div id="left-math-analysis-box" style="background:rgba(2,4,9,0.8); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px 10px; font-family:var(--font-mono); font-size:0.68rem;">
                        <div style="color:var(--text-dim); margin-bottom:3px;">FORMULA:</div>
                        <div id="left-math-formula" style="color:var(--neon-cyan); word-break:break-all;">Damage = Base * Type Multiplier (+50% Adv / -50% Disadv / Normal)</div>
                        <div id="left-math-ev" style="color:#94a3b8; margin-top:4px;">EV: +0.5000 &bull; Knockout: 50% &bull; Risk: LOW</div>
                    </div>

                    <!-- CONTROLS -->
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <button id="btn-compute-winning-route" class="btn-action-main" style="width:100%; padding:9px; font-size:0.78rem; border-color:var(--neon-cyan);" onclick="fetchStrategicAiAnalysis('BALANCED')">
                            🧠 COMPUTE WINNING ROUTE
                        </button>
                        <button id="btn-execute-ai" class="btn-action-main" style="width:100%; padding:9px; font-size:0.78rem; border-color:var(--neon-green); color:#fff;" onclick="executeAiRecommendation()">
                            ⚡ EXECUTE AI PLAY
                        </button>
                    </div>
                </div>


                <!-- CENTER COLUMN: TCG BATTLE ARENA PLAYMAT -->
                <div class="tcg-playmat-container">
                    <!-- SETUP PHASE BANNER -->
                    <div id="match-setup-banner" style="display:none; background:rgba(0,243,255,0.08); border:1px solid var(--neon-cyan); border-radius:8px; padding:12px 16px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                            <div>
                                <div style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:900; color:var(--neon-cyan);">
                                    🎯 INITIAL SETUP: PLACE BASIC POKÉMON (4-CARD HAND)
                                </div>
                                <div style="font-size:0.75rem; color:#cbd5e1; margin-top:2px;">
                                    Place 1 Basic Pokémon into Active Spot (Main) and up to 3 into Bench Slots.
                                </div>
                            </div>
                            <div style="display:flex; gap:8px; flex-wrap:wrap;">
                                <button id="btn-quick-start" class="btn-action-main" style="background:linear-gradient(135deg, #00f3ff, #00ff88); color:#000; font-weight:900; border:none; padding:6px 14px; font-size:0.75rem;" onclick="autoPlaceSetupAndBattle()">
                                    ⚡ QUICK START (AUTO-PLACE & BATTLE)
                                </button>
                                <button id="btn-mulligan" class="btn-cyber-sm" style="border-color:var(--neon-amber); color:#fef08a; padding:6px 12px; font-size:0.75rem;" onclick="triggerMulligan()">
                                    🔄 MULLIGAN REDRAW
                                </button>
                                <button id="btn-confirm-setup" class="btn-action-main" style="border-color:var(--neon-green); padding:6px 14px; font-size:0.75rem;" onclick="confirmInitialSetup()">
                                    ✅ CONFIRM SETUP
                                </button>
                            </div>
                        </div>
                        <div id="setup-ai-rec-box" style="display:none; margin-top:10px; background:rgba(2,6,18,0.85); border:1px solid rgba(0,243,255,0.4); border-radius:6px; padding:8px 12px; font-size:0.75rem;">
                        </div>
                    </div>

                    <!-- OPPONENT HAND CARDS (FACE-DOWN CARD BACKS - HIDDEN FROM PLAYER) -->
                    <div style="margin-bottom:10px;">
                        <div class="section-label" style="color:var(--neon-magenta);"><span>AI HAND (<span id="opp-hand-count-label">5</span> CARDS FACE-DOWN)</span></div>
                        <div id="opp-hand-view" class="hand-grid" style="pointer-events:none; user-select:none; opacity:0.9;"></div>
                    </div>

                    <!-- OPPONENT TOP BOARD: BENCH & FACE-DOWN DECK PILE -->
                    <div style="display:flex; gap:14px; align-items:flex-start;">
                        <div style="flex:1;">
                            <div class="section-label" style="color:var(--neon-magenta);"><span>OPPONENT BENCH POKÉMON (MAX 3 SLOTS)</span></div>
                            <div id="opp-bench-view" class="bench-grid"></div>
                        </div>
                        <div style="display:flex; flex-direction:column; align-items:center;">
                            <div class="section-label" style="color:var(--neon-magenta); font-size:0.65rem;"><span>AI DECK (FACE-DOWN)</span></div>
                            <div id="opp-face-down-deck" class="face-down-deck-box opp-deck" title="AI Opponent Deck (Strictly Isolated - Cannot be viewed or drawn by player)">
                                <div class="deck-card-back-pattern">
                                    <div class="deck-pokeball-icon" style="box-shadow:0 0 10px rgba(255,0,127,0.4);">
                                        <div class="deck-pokeball-center"></div>
                                    </div>
                                    <div class="deck-counter-badge" style="color:#f472b6;"><span id="opp-deck-count">55</span></div>
                                    <div style="font-size:0.55rem; color:#fca5a5; font-family:var(--font-mono); margin-top:2px;">CARDS</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- OPPONENT MAIN POKÉMON -->
                    <div class="active-spot-center">
                        <div class="section-label" style="color:var(--neon-magenta);"><span>👑 OPPONENT ACTIVE POKÉMON</span></div>
                        <div id="opp-active-view" class="visual-active-card opp-active-card"></div>
                    </div>

                    <!-- ARENA DIVIDER -->
                    <div class="arena-divider-bar">
                        <div class="divider-line"></div>
                        <div class="divider-badge">⚡ COMPETITIVE MATCH ARENA ⚡</div>
                        <div class="divider-line"></div>
                    </div>

                    <!-- PLAYER MAIN POKÉMON -->
                    <div class="active-spot-center">
                        <div class="section-label" style="color:var(--neon-cyan);"><span>👑 YOUR ACTIVE POKÉMON</span></div>
                        <div id="player-active-view" class="visual-active-card"></div>
                    </div>

                    <!-- PLAYER BOTTOM BOARD: SUB POKÉMON -->
                    <div>
                        <div class="section-label" style="color:var(--neon-cyan);"><span>YOUR BENCH POKÉMON (MAX 3 SLOTS)</span></div>
                        <div id="player-bench-view" class="bench-grid"></div>
                    </div>

                    <!-- PLAYER HAND CARDS & FACE-DOWN DRAW PILE -->
                    <div style="display:flex; gap:14px; align-items:flex-start;">
                        <div style="flex:1;">
                            <div class="section-label"><span>YOUR HAND CARDS (<span id="hand-count-label">5</span> CARDS)</span></div>
                            <div id="player-hand-view" class="hand-grid"></div>
                        </div>
                        <div style="display:flex; flex-direction:column; align-items:center;">
                            <div class="section-label" style="color:var(--neon-cyan); font-size:0.65rem;"><span>YOUR DECK (DRAW PILE)</span></div>
                            <div id="player-face-down-deck" class="face-down-deck-box" onclick="claimRandomDeckCard()" title="Click to draw 1 card from your 60-card face-down deck (1/turn)">
                                <div class="deck-card-back-pattern">
                                    <div class="deck-pokeball-icon">
                                        <div class="deck-pokeball-center"></div>
                                    </div>
                                    <div class="deck-counter-badge"><span id="p-deck-count-visual">55</span></div>
                                    <div style="font-size:0.55rem; color:var(--neon-cyan); font-family:var(--font-mono); margin-top:2px;">DRAW PILE</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- SETUP BOTTOM ACTIONS BAR (Active during SETUP phase) -->
                    <div id="setup-bottom-actions-bar" class="match-actions-bar" style="display:none; background:rgba(0,243,255,0.08); border:1px solid var(--neon-cyan); border-radius:8px; padding:10px 14px; margin-top:12px;">
                        <button class="btn-action-main" style="background:linear-gradient(135deg, #00f3ff, #00ff88); color:#000; font-weight:900; border:none; padding:8px 18px; font-size:0.8rem; box-shadow:0 0 15px rgba(0,255,136,0.4);" onclick="autoPlaceSetupAndBattle()">
                            ⚡ AUTO-PLACE & START BATTLE
                        </button>
                        <button class="btn-cyber-sm" style="border-color:var(--neon-amber); color:#fef08a; padding:8px 14px; font-size:0.75rem;" onclick="triggerMulligan()">
                            🔄 MULLIGAN REDRAW
                        </button>
                        <button class="btn-action-main" style="border-color:var(--neon-green); padding:8px 16px; font-size:0.78rem;" onclick="confirmInitialSetup()">
                            ✅ CONFIRM SETUP
                        </button>
                        <button class="btn-cyber-sm" style="border-color:var(--neon-cyan); color:#38bdf8; padding:8px 14px; font-size:0.75rem;" onclick="switchMode('cards')">
                            🎴 EDIT DECK
                        </button>
                    </div>

                    <!-- MATCH CONTROLS (Active during BATTLE phase) -->
                    <div id="match-actions-bar" class="match-actions-bar">
                        <button id="btn-claim-deck-card" class="btn-action-main" style="border-color:var(--neon-cyan); padding:8px 14px; font-size:0.75rem;" onclick="claimRandomDeckCard()">
                            🃏 DRAW CARD (1/TURN) (<span id="p-deck-count">55</span> LEFT)
                        </button>
                        <button id="btn-add-energy-main" class="btn-action-main" style="border-color:var(--neon-amber); padding:8px 14px; font-size:0.75rem;" onclick="promptAddEnergyDirect('player')">
                            ⚡ + ATTACH ENERGY (1/TURN)
                        </button>
                        <button id="btn-switch-retreat" class="btn-action-main" style="border-color:var(--neon-purple); padding:8px 14px; font-size:0.75rem;" onclick="openSwitchModal()">
                            🔄 SWITCH / RETREAT
                        </button>
                        <button id="btn-end-turn" class="btn-action-main" style="border-color:var(--neon-green); padding:8px 14px; font-size:0.75rem;" onclick="endPlayerTurn()">
                            ⏭️ END TURN & LET OPPONENT PLAY
                        </button>
                    </div>
                </div>

                <!-- RIGHT COLUMN: SCOREBOARD & LOGS -->
                <div class="side-column-panel">
                    <div class="section-label"><span>📊 SCOREBOARD & LOGS</span></div>
                    <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(0,243,255,0.2); border-radius:8px; padding:10px;">
                        <div style="display:flex; justify-content:space-between; font-family:var(--font-orbitron); font-size:0.85rem;">
                            <span style="color:var(--neon-green);">YOUR PRIZES: <b id="p-ko-count" style="font-size:1.1rem;">0</b>/6</span>
                            <span style="color:var(--neon-magenta);">OPP PRIZES: <b id="opp-ko-count" style="font-size:1.1rem;">0</b>/6</span>
                        </div>
                        <div id="match-status-banner" class="cyber-badge" style="margin-top:8px; width:100%; justify-content:center;">MATCH IN PROGRESS</div>
                    </div>

                    <div>
                        <button class="btn-action-main" style="width:100%; padding:8px; font-size:0.75rem; margin-bottom:8px;" onclick="switchMode('cards')">
                            🎴 60-CARD DECK BUILDER
                        </button>
                        <button class="btn-cyber-sm" style="width:100%; padding:8px; font-size:0.75rem;" onclick="startNewMatch()">
                            🔄 RESTART MATCH
                        </button>
                    </div>

                    <div class="section-label" style="color:var(--neon-green);"><span>COMBAT LOG</span></div>
                    <div id="combat-log" class="combat-log-box"></div>
                </div>
            </div>
        </div>

        <!-- SWITCH / RETREAT MODAL -->
        <div id="switch-modal" class="modal-overlay" style="display:none;">
            <div class="modal-card" style="max-width:440px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="font-family:var(--font-orbitron); font-size:1.05rem; font-weight:900; color:var(--neon-purple);">
                        🔄 SELECT BENCH POKÉMON TO SWITCH
                    </div>
                    <button style="background:none; border:none; color:var(--text-dim); font-size:1.2rem; cursor:pointer;" onclick="closeSwitchModal()">✕</button>
                </div>
                <div style="font-size:0.78rem; color:#cbd5e1; margin-bottom:12px;">
                    Choose one of your benched Pokémon to swap into the Active Spot. Attached Energy cards remain on both Pokémon.
                </div>
                <div id="switch-bench-list" style="display:flex; flex-direction:column; gap:8px;"></div>
            </div>
        </div>

        <!-- KNOCKOUT PROMOTION MODAL -->
        <div id="ko-modal" class="modal-overlay" style="display:none;">
            <div class="modal-card" style="max-width:440px; border-color:#ef4444;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="font-family:var(--font-orbitron); font-size:1.05rem; font-weight:900; color:#ef4444;">
                        ⚠️ ACTIVE KNOCKED OUT: PROMOTE BENCH
                    </div>
                </div>
                <div style="font-size:0.78rem; color:#cbd5e1; margin-bottom:12px;">
                    Your Active Pokémon was Knocked Out! Select a benched Pokémon to become your new Active Pokémon.
                </div>
                <div id="ko-bench-list" style="display:flex; flex-direction:column; gap:8px;"></div>
            </div>
        </div>

        <!-- ================= VIEW 4: PRE-SET META ARCHETYPES ================= -->
        <div id="view-deck" style="display:none;" class="all-cards-section">
            <div style="font-family:var(--font-orbitron); font-size:1.2rem; font-weight:900; color:var(--neon-cyan); margin-bottom:12px;">
                🏆 OFFICIAL CHAMPIONSHIP META PRESETS
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px;">
                <button class="btn-cyber-sm" onclick="renderDeckBuilderPreview('charizard-ex-pidgeot')">Charizard ex / Pidgeot ex</button>
                <button class="btn-cyber-sm" onclick="renderDeckBuilderPreview('miraidon-ex-regieleki')">Miraidon ex / Regieleki</button>
                <button class="btn-cyber-sm" onclick="renderDeckBuilderPreview('gardevoir-ex')">Gardevoir ex / Scream Tail</button>
            </div>
            <div id="deck-preview-cards" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:10px;"></div>
        </div>

        <!-- ================= VIEW 5: PACK HISTORY ================= -->
        <div id="view-history" style="display:none;" class="all-cards-section">
            <div style="font-family:var(--font-orbitron); font-size:1.2rem; font-weight:900; color:var(--neon-cyan); margin-bottom:12px;">
                📜 YOUR PACK OPENING HISTORY
            </div>
            <div id="pack-history-list" style="display:flex; flex-direction:column; gap:12px;"></div>
        </div>
    </div>

    <!-- AUTH MODAL (LOGIN & CREATE ACCOUNT) -->
    <div id="auth-modal" class="modal-overlay" style="display:none;">
        <div class="modal-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div id="auth-modal-title" style="font-family:var(--font-orbitron); font-size:1.15rem; font-weight:900; color:var(--neon-cyan);">
                    🔑 LOGIN TO YOUR ACCOUNT
                </div>
                <button style="background:none; border:none; color:var(--text-dim); font-size:1.2rem; cursor:pointer;" onclick="hideAuthModal()">✕</button>
            </div>

            <!-- Login Form -->
            <div id="form-login">
                <label style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">USERNAME OR EMAIL</label>
                <input type="text" id="login-ident" class="neon-input" placeholder="e.g. TrainerAsh or ash@pokemon.com">

                <label style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">PASSWORD</label>
                <input type="password" id="login-pass" class="neon-input" placeholder="Enter your password">

                <div id="login-error" style="color:#f87171; font-size:0.78rem; margin-bottom:10px; display:none;"></div>

                <button class="btn-action-main" style="width:100%; padding:10px; font-size:0.85rem;" onclick="submitLogin()">
                    [ LOGIN ]
                </button>

                <div style="margin-top:14px; text-align:center; font-size:0.8rem; color:var(--text-dim);">
                    Don't have an account? <a href="javascript:void(0)" style="color:var(--neon-cyan); text-decoration:none; font-weight:700;" onclick="toggleAuthMode('register')">Create Account</a>
                </div>
            </div>

            <!-- Register Form -->
            <div id="form-register" style="display:none;">
                <label style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">USERNAME</label>
                <input type="text" id="reg-username" class="neon-input" placeholder="Choose a trainer name (min 3 chars)">

                <label style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">EMAIL ADDRESS</label>
                <input type="email" id="reg-email" class="neon-input" placeholder="e.g. ash@pokemon.com">

                <label style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">PASSWORD</label>
                <input type="password" id="reg-pass" class="neon-input" placeholder="Min 6 characters">

                <label style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">CONFIRM PASSWORD</label>
                <input type="password" id="reg-confirm-pass" class="neon-input" placeholder="Re-enter password">

                <div id="reg-error" style="color:#f87171; font-size:0.78rem; margin-bottom:10px; display:none;"></div>

                <button class="btn-action-main" style="width:100%; padding:10px; font-size:0.85rem; border-color:var(--neon-green);" onclick="submitRegister()">
                    [ CREATE ACCOUNT ]
                </button>

                <div style="margin-top:14px; text-align:center; font-size:0.8rem; color:var(--text-dim);">
                    Already have an account? <a href="javascript:void(0)" style="color:var(--neon-cyan); text-decoration:none; font-weight:700;" onclick="toggleAuthMode('login')">Login</a>
                </div>
            </div>
        </div>
    </div>

    <!-- JAVASCRIPT APP LOGIC -->
    <script>
        // ================= GLOBAL STATE =================
        let CURRENT_USER = null;
        let AUTH_TOKEN = localStorage.getItem('pokemon_tcg_token') || null;
        let OWNED_CARDS = [];
        let OWNED_CARDS_MAP = {};
        let ALL_CARDS_MAP = {};
        let ALL_CARDS_LIST = [];
        let SELECTED_CARD_KEY = null;
        let SELECTED_CARD_ID = null;
        let SELECTED_CARD_DATA = null;

        function selectHandCard(handKey, cardName, cardData, event) {
            if (event) event.stopPropagation();
            if (!handKey) {
                SELECTED_CARD_KEY = null;
                SELECTED_CARD_ID = null;
                SELECTED_CARD_DATA = null;
                if (CURRENT_MATCH_STATE) updateMatchView(CURRENT_MATCH_STATE);
                return;
            }

            let actualData = cardData;
            if (typeof cardData === 'number' && CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.hand) {
                actualData = CURRENT_MATCH_STATE.player.hand[cardData] || cardName;
            }
            const cname = cardName || (actualData && (actualData.name || actualData.card_name)) || '';
            const meta = getCardMeta(cname);
            const isEnergy = (meta && meta.card_type === 'energy') || cname.toLowerCase().includes('energy');

            // Enforce 1 Energy attachment per turn rule
            if (isEnergy && CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.phase !== 'SETUP') {
                const alreadyAttached = CURRENT_MATCH_STATE.energy_attached_this_turn || CURRENT_MATCH_STATE.hasAttachedEnergyThisTurn;
                if (alreadyAttached) {
                    alert("⚠️ You have already attached Energy this turn.");
                    return;
                }
            }

            if (SELECTED_CARD_KEY === handKey) {
                SELECTED_CARD_KEY = null;
                SELECTED_CARD_ID = null;
                SELECTED_CARD_DATA = null;
                console.log("[CARD] Deselected card");
            } else {
                SELECTED_CARD_KEY = handKey;
                SELECTED_CARD_ID = (actualData && actualData.card_id) || cname;
                SELECTED_CARD_DATA = actualData || cname;
                console.log("[CARD] Selected:", SELECTED_CARD_ID, cname);
            }
            if (CURRENT_MATCH_STATE) {
                updateMatchView(CURRENT_MATCH_STATE);
            }
        }

        async function playSelectedCard(target = 'active') {
            if (!SELECTED_CARD_DATA && !SELECTED_CARD_KEY) return;
            const cname = typeof SELECTED_CARD_DATA === 'string' 
                ? SELECTED_CARD_DATA 
                : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name || SELECTED_CARD_ID);
            SELECTED_CARD_KEY = null;
            SELECTED_CARD_ID = null;
            SELECTED_CARD_DATA = null;
            if (CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.phase === 'SETUP') {
                if (target === 'active') {
                    await setupPlaceActive(cname);
                } else {
                    await setupPlaceBench(cname);
                }
                return;
            }
            await matchPlayCard(cname, target);
        }

        async function loadAllCards() {
            try {
                const res = await fetch('/api/v1/cards/all');
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.cards) {
                        ALL_CARDS_LIST = data.cards;
                        ALL_CARDS_MAP = {};
                        data.cards.forEach(c => {
                            if (c.card_id) ALL_CARDS_MAP[String(c.card_id).trim()] = c;
                            if (c.name) ALL_CARDS_MAP[String(c.name).toLowerCase().trim()] = c;
                            if (c.card_name) ALL_CARDS_MAP[String(c.card_name).toLowerCase().trim()] = c;
                        });
                    }
                }
            } catch (err) {
                console.warn("Notice: /api/v1/cards/all fetch error:", err);
            }
        }

        function getCardImageUrl(meta, cardName) {
            if (meta && meta.image && meta.image.startsWith('/static/')) return meta.image;
            if (meta && meta.card_id) {
                const cid = String(meta.card_id).trim();
                const m = ALL_CARDS_MAP[cid];
                if (m && m.image) return m.image;
                return `/static/card_images/${cid}.png`;
            }
            if (cardName) {
                const clean = String(cardName).toLowerCase().trim();
                const m = ALL_CARDS_MAP[clean] || OWNED_CARDS_MAP[clean];
                if (m && m.image) return m.image;
                if (clean.includes('energy')) return '/static/card_images/placeholder_energy.svg';
                if (clean.includes('potion') || clean.includes('ball') || clean.includes('switch') || clean.includes('rope')) return '/static/card_images/placeholder_item.svg';
                if (clean.includes('research') || clean.includes('boss') || clean.includes('supporter') || clean.includes('iono')) return '/static/card_images/placeholder_supporter.svg';
            }
            return '/static/card_images/placeholder_card.svg';
        }
        
        function getRandomBasicPokemon(count = 4, exclude = []) {
            const pool = ["Pikachu", "Charmander", "Squirtle", "Bulbasaur", "Eevee", "Machop", "Geodude", "Abra", "Meowth", "Gastly", "Psyduck", "Snorlax"];
            const exSet = new Set((exclude || []).map(e => (typeof e === 'string' ? e : e.name).toLowerCase()));
            const chosen = [];
            for (const p of pool) {
                if (chosen.length >= count) break;
                if (!exSet.has(p.toLowerCase())) chosen.push(p);
            }
            return chosen.slice(0, count);
        }

        // 3-Deck Builder State
        let USER_DECKS = [
            { slot: 1, name: "My Deck 1", cards: [], is_active: 1 },
            { slot: 2, name: "My Deck 2", cards: [], is_active: 0 },
            { slot: 3, name: "My Deck 3", cards: [], is_active: 0 }
        ];
        let ACTIVE_DECK_SLOT = 1;
        let CHOSEN_4_CARDS = getRandomBasicPokemon(4);
        let OPPONENT_4_CARDS = getRandomBasicPokemon(4, CHOSEN_4_CARDS);
        // Only Basic Pokémon can be chosen for starting slots
        function isBasicPokemon(c) {
            const meta = getCardMeta(c);
            return (meta && meta.card_type === 'pokemon' && meta.stage === 'Basic');
        }
        let CURRENT_MATCH_STATE = null;
        let CURRENT_PACK_REVEAL = [];
        let FILTER_CATEGORY = 'all';
        let FILTER_STAGE = 'all';
        let FILTER_RARITY = 'all';
        let SEARCH_QUERY = '';
        let IS_AI_PROCESSING = false;
        let filterDebounceTimer = null;

        const ENERGY_EMOJI_MAP = {
            'Grass': '🌿', 'Fire': '🔥', 'Water': '💧', 'Lightning': '⚡',
            'Fighting': '🥊', 'Psychic': '🔮', 'Darkness': '🌑', 'Metal': '⚙️',
            'Dragon': '🐉', 'Colorless': '⚪'
        };

        function normalizeEnergyTypeJs(val) {
            if (!val) return 'Colorless';
            if (typeof val === 'object') {
                val = val.energy_type || val.pokemon_type || val.type || val.name || 'Colorless';
            }
            let s = String(val).trim().replace(/[{}]/g, '');
            let sLow = s.toLowerCase();
            if (s === 'G' || sLow.includes('grass')) return 'Grass';
            if (s === 'R' || sLow.includes('fire')) return 'Fire';
            if (s === 'W' || sLow.includes('water')) return 'Water';
            if (s === 'L' || sLow.includes('lightning') || sLow.includes('electric')) return 'Lightning';
            if (s === 'F' || sLow.includes('fighting')) return 'Fighting';
            if (s === 'P' || sLow.includes('psychic')) return 'Psychic';
            if (s === 'D' || sLow.includes('dark')) return 'Darkness';
            if (s === 'M' || sLow.includes('metal') || sLow.includes('steel')) return 'Metal';
            if (s === 'N' || sLow.includes('dragon')) return 'Dragon';
            return 'Colorless';
        }

        function formatCostEmojisJs(costList) {
            if (!costList || costList.length === 0) return '⚪ (Free)';
            return costList.map(c => ENERGY_EMOJI_MAP[normalizeEnergyTypeJs(c)] || '⚪').join(' ');
        }

        function canPayAttackCostDetails(attachedEnergies, costList) {
            if (!costList || costList.length === 0) {
                return { canAfford: true, reason: 'Ready to attack!', costEmojis: '⚪ (Free)', missing: {} };
            }
            const energyList = attachedEnergies || [];
            const required = {};
            let colorlessNeeded = 0;
            const normCost = [];

            for (let c of costList) {
                let norm = normalizeEnergyTypeJs(c);
                normCost.push(norm);
                if (norm === 'Colorless') {
                    colorlessNeeded++;
                } else {
                    required[norm] = (required[norm] || 0) + 1;
                }
            }

            const attachedCounts = {};
            const cleanAttached = [];
            for (let e of energyList) {
                let norm = normalizeEnergyTypeJs(e);
                cleanAttached.push(norm);
                attachedCounts[norm] = (attachedCounts[norm] || 0) + 1;
            }

            const costEmojis = formatCostEmojisJs(costList);
            const missing = {};

            // 1. Pay specific elemental requirements first
            for (let reqType in required) {
                let reqAmt = required[reqType];
                let haveAmt = attachedCounts[reqType] || 0;
                if (haveAmt < reqAmt) {
                    let deficit = reqAmt - haveAmt;
                    missing[reqType] = deficit;
                    attachedCounts[reqType] = 0;
                } else {
                    attachedCounts[reqType] -= reqAmt;
                }
            }

            if (Object.keys(missing).length > 0) {
                let deficitStrs = Object.entries(missing).map(([etype, cnt]) => `Need ${cnt} more ${etype} Energy`);
                return {
                    canAfford: false,
                    reason: deficitStrs.join(', '),
                    costEmojis: costEmojis,
                    missing: missing
                };
            }

            // 2. Pay colorless requirements with any leftover attached energy
            let totalLeftover = 0;
            for (let t in attachedCounts) {
                totalLeftover += (attachedCounts[t] || 0);
            }

            if (totalLeftover < colorlessNeeded) {
                let deficit = colorlessNeeded - totalLeftover;
                missing['Colorless'] = deficit;
                return {
                    canAfford: false,
                    reason: `Need ${deficit} more Energy (any type) for Colorless cost`,
                    costEmojis: costEmojis,
                    missing: missing
                };
            }

            return {
                canAfford: true,
                reason: 'Ready to attack!',
                costEmojis: costEmojis,
                missing: {}
            };
        }

        function canPayAttackCost(attachedEnergies, costList) {
            return canPayAttackCostDetails(attachedEnergies, costList).canAfford;
        }

        const TYPE_ADVANTAGES_JS = {
            'Water': ['Fire', 'Fighting'],
            'Fire': ['Grass', 'Metal'],
            'Grass': ['Water', 'Fighting'],
            'Lightning': ['Water'],
            'Fighting': ['Darkness', 'Metal', 'Colorless'],
            'Psychic': ['Fighting'],
            'Darkness': ['Psychic'],
            'Metal': ['Grass', 'Psychic'],
            'Dragon': ['Dragon'],
            'Colorless': []
        };

        const TYPE_DISADVANTAGES_JS = {
            'Water': ['Grass', 'Lightning'],
            'Fire': ['Water'],
            'Grass': ['Fire'],
            'Lightning': ['Fighting'],
            'Fighting': ['Psychic', 'Grass'],
            'Psychic': ['Darkness', 'Metal'],
            'Darkness': ['Fighting', 'Grass'],
            'Metal': ['Fire', 'Fighting'],
            'Dragon': [],
            'Colorless': ['Fighting']
        };

        function getTypeEffectivenessJs(atkType, defType, defWeak, defRes, atkWeak) {
            const aNorm = normalizeEnergyTypeJs(atkType);
            const dNorm = normalizeEnergyTypeJs(defType);
            const dw = (defWeak || '').toLowerCase();
            const dr = (defRes || '').toLowerCase();
            const aw = (atkWeak || '').toLowerCase();

            if (dw && dw.includes(aNorm.toLowerCase())) {
                return { mult: 1.5, label: 'ADVANTAGE', desc: `+50% Type Advantage (vs ${dNorm})` };
            }
            if (dr && dr.includes(aNorm.toLowerCase())) {
                return { mult: 0.5, label: 'DISADVANTAGE', desc: `-50% Type Disadvantage (vs ${dNorm})` };
            }
            if (aw && aw.includes(dNorm.toLowerCase())) {
                return { mult: 0.5, label: 'DISADVANTAGE', desc: `-50% Type Disadvantage (vs ${dNorm})` };
            }

            const advs = TYPE_ADVANTAGES_JS[aNorm] || [];
            if (advs.includes(dNorm)) {
                return { mult: 1.5, label: 'ADVANTAGE', desc: `+50% Type Advantage (vs ${dNorm})` };
            }
            const disadvs = TYPE_DISADVANTAGES_JS[aNorm] || [];
            if (disadvs.includes(dNorm)) {
                return { mult: 0.5, label: 'DISADVANTAGE', desc: `-50% Type Disadvantage (vs ${dNorm})` };
            }

            return { mult: 1.0, label: 'NEUTRAL', desc: `Normal DMG (vs ${dNorm})` };
        }

        function calculateMatchupDamageJs(baseDmg, atkType, defType, defWeak, defRes, atkWeak) {
            if (!baseDmg || baseDmg <= 0) return { finalDmg: 0, mult: 1.0, label: 'NEUTRAL', desc: 'No DMG' };
            const eff = getTypeEffectivenessJs(atkType, defType, defWeak, defRes, atkWeak);
            const finalDmg = Math.max(1, Math.round(baseDmg * eff.mult));
            return { finalDmg, mult: eff.mult, label: eff.label, desc: eff.desc };
        }

        function loadTop60RecommendedDeck() {
            startNewMatch();
        }

        function startMatchWithCustomDeck() {
            startBattleWithSelected4Cards();
        }

        // ================= 1. AUTHENTICATION & SESSIONS =================
        async function checkAuthSession() {
            if (!AUTH_TOKEN) {
                renderLoggedOutState();
                return;
            }
            try {
                const res = await fetch('/api/v1/auth/me', {
                    headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
                });
                const data = await res.json();
                if (data.status === 'success' && data.user) {
                    CURRENT_USER = data.user;
                    renderLoggedInState(data.user, data.stats);
                    loadUserCollection();
                } else {
                    handleLogout();
                }
            } catch (err) {
                console.error("Session check failed:", err);
                renderLoggedOutState();
            }
        }

        function renderLoggedInState(user, stats) {
            document.getElementById('user-profile-bar').style.display = 'flex';
            document.getElementById('logged-out-banner').style.display = 'none';
            document.getElementById('header-username').textContent = user.username;
            document.getElementById('header-user-avatar').textContent = user.username.charAt(0).toUpperCase();

            if (stats) updateCollectionStatsUI(stats);
            loadUserDecks();
        }

        function renderLoggedOutState() {
            CURRENT_USER = null;
            AUTH_TOKEN = null;
            localStorage.removeItem('pokemon_tcg_token');
            document.getElementById('user-profile-bar').style.display = 'none';
            document.getElementById('logged-out-banner').style.display = 'flex';
        }

        function updateCollectionStatsUI(stats) {
            document.getElementById('stat-total-cards').textContent = stats.total_cards || 0;
            document.getElementById('stat-pokemon-cards').textContent = stats.pokemon || 0;
            document.getElementById('stat-trainer-cards').textContent = stats.trainer || 0;
            document.getElementById('stat-energy-cards').textContent = stats.energy || 0;
        }

        function showAuthModal(mode) {
            const modal = document.getElementById('auth-modal');
            modal.style.display = 'flex';
            toggleAuthMode(mode);
        }

        function hideAuthModal() {
            document.getElementById('auth-modal').style.display = 'none';
        }

        function toggleAuthMode(mode) {
            const isReg = mode === 'register';
            document.getElementById('form-login').style.display = isReg ? 'none' : 'block';
            document.getElementById('form-register').style.display = isReg ? 'block' : 'none';
            document.getElementById('auth-modal-title').textContent = isReg ? '📝 CREATE YOUR ACCOUNT' : '🔑 LOGIN TO YOUR ACCOUNT';
            document.getElementById('login-error').style.display = 'none';
            document.getElementById('reg-error').style.display = 'none';
        }

        async function submitLogin() {
            const ident = document.getElementById('login-ident').value.trim();
            const pass = document.getElementById('login-pass').value;
            const errEl = document.getElementById('login-error');

            if (!ident || !pass) {
                errEl.textContent = "Please enter username/email and password.";
                errEl.style.display = 'block';
                return;
            }

            try {
                const res = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username_or_email: ident, password: pass })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    AUTH_TOKEN = data.token;
                    localStorage.setItem('pokemon_tcg_token', data.token);
                    CURRENT_USER = data.user;
                    hideAuthModal();
                    await checkAuthSession();
                } else {
                    errEl.textContent = data.detail || "Invalid login credentials.";
                    errEl.style.display = 'block';
                }
            } catch (err) {
                errEl.textContent = "Connection error. Please try again.";
                errEl.style.display = 'block';
            }
        }

        async function submitRegister() {
            const uname = document.getElementById('reg-username').value.trim();
            const email = document.getElementById('reg-email').value.trim();
            const pass = document.getElementById('reg-pass').value;
            const conf = document.getElementById('reg-confirm-pass').value;
            const errEl = document.getElementById('reg-error');

            if (pass !== conf) {
                errEl.textContent = "Passwords do not match.";
                errEl.style.display = 'block';
                return;
            }

            try {
                const res = await fetch('/api/v1/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: uname, email: email, password: pass, confirm_password: conf })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    AUTH_TOKEN = data.token;
                    localStorage.setItem('pokemon_tcg_token', data.token);
                    CURRENT_USER = data.user;
                    hideAuthModal();
                    await checkAuthSession();
                } else {
                    errEl.textContent = data.detail || "Registration failed. Please check inputs.";
                    errEl.style.display = 'block';
                }
            } catch (err) {
                errEl.textContent = "Connection error. Please try again.";
                errEl.style.display = 'block';
            }
        }

        async function handleLogout() {
            if (AUTH_TOKEN) {
                try {
                    await fetch('/api/v1/auth/logout', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
                    });
                } catch(e) {}
            }
            renderLoggedOutState();
            OWNED_CARDS = [];
            OWNED_CARDS_MAP = {};
            renderOwnedCardsGrid();
        }

        // ================= 2. MODE & TAB SWITCHING =================
        function switchMode(mode) {
            if (mode === 'match') {
                const activeDeck = USER_DECKS.find(d => d.is_active) || USER_DECKS[0];
                if (!CURRENT_MATCH_STATE && (!activeDeck || !activeDeck.cards || activeDeck.cards.length === 0)) {
                    switchMode('cards');
                    showDeckBuilderEmptyPrompt();
                    return;
                }
            }

            const views = {
                'match': document.getElementById('view-match'),
                'pack': document.getElementById('view-pack'),
                'cards': document.getElementById('view-cards'),
                'deck': document.getElementById('view-deck'),
                'history': document.getElementById('view-history')
            };
            const btns = {
                'match': document.getElementById('tab-btn-match'),
                'pack': document.getElementById('tab-btn-pack'),
                'cards': document.getElementById('tab-btn-cards'),
                'deck': document.getElementById('tab-btn-deck'),
                'history': document.getElementById('tab-btn-history')
            };

            Object.values(views).forEach(v => { if (v) v.style.display = 'none'; });
            Object.values(btns).forEach(b => { if (b) b.classList.remove('active'); });

            if (views[mode]) views[mode].style.display = 'block';
            if (btns[mode]) btns[mode].classList.add('active');

            if (mode === 'cards') {
                loadUserCollection();
            } else if (mode === 'history') {
                loadPackHistory();
            } else if (mode === 'deck') {
                renderDeckBuilderPreview('charizard-ex-pidgeot');
            }
        }

        // ================= 3. BOOSTER PACK OPENING ENGINE =================
        async function openBoosterPack() {
            if (!CURRENT_USER) {
                showAuthModal('login');
                return;
            }

            const btn = document.getElementById('btn-open-pack');
            if (btn) btn.disabled = true;

            try {
                const res = await fetch('/api/v1/pack/open', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
                });
                const data = await res.json();
                if (data.status === 'success') {
                    CURRENT_PACK_REVEAL = data.cards;
                    updateCollectionStatsUI(data.collection_stats);
                    renderPackRevealStage(data.cards);
                    loadUserCollection(false);
                } else {
                    alert(data.detail || "Unable to open pack right now.");
                }
            } catch (err) {
                alert("Network error opening booster pack. Please try again.");
            } finally {
                if (btn) btn.disabled = false;
            }
        }

        function renderPackRevealStage(cards) {
            const area = document.getElementById('pack-reveal-area');
            const grid = document.getElementById('pack-cards-grid');
            const summary = document.getElementById('pack-summary-dock');
            const countEl = document.getElementById('revealed-count');

            area.style.display = 'flex';
            summary.style.display = 'none';
            grid.innerHTML = '';
            countEl.textContent = '0';

            cards.forEach((card, idx) => {
                const wrapper = document.createElement('div');
                wrapper.className = 'card-flip-wrapper';
                wrapper.id = `pack-card-wrap-${idx}`;

                const rarityClass = getRarityClass(card.rarity);
                const isDup = card.is_duplicate;
                const prevQty = card.previous_quantity || 0;
                const newQty = card.quantity || 1;

                const dupBadge = isDup
                    ? `<span style="background:rgba(245,158,11,0.25); border:1px solid #f59e0b; color:#fde68a; font-size:0.65rem; padding:2px 6px; border-radius:4px; font-weight:800;">🔁 DUPLICATE (+1) [Now: ×${newQty}]</span>`
                    : `<span style="background:rgba(0,255,136,0.2); border:1px solid #00ff88; color:#86efac; font-size:0.65rem; padding:2px 6px; border-radius:4px; font-weight:800;">✨ NEW CARD!</span>`;

                wrapper.innerHTML = `
                    <div class="card-flip-inner">
                        <!-- FACE DOWN -->
                        <div class="card-face card-face-back">
                            <div style="font-size:2.8rem; margin-bottom:6px;">🎴</div>
                            <div style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:900; color:var(--neon-cyan);">POKÉMON TCG</div>
                            <div style="font-size:0.68rem; color:#cbd5e1; margin-top:4px;">CARD #${idx+1}</div>
                            <div style="font-size:0.65rem; color:var(--neon-green); margin-top:14px; font-weight:700;">[ CLICK TO FLIP ]</div>
                        </div>

                        <!-- FACE UP -->
                        <div class="card-face card-face-front ${rarityClass}">
                            <div>
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="font-family:var(--font-mono); font-size:0.65rem; color:var(--text-dim);">${card.card_type.toUpperCase()}</span>
                                    <span style="font-family:var(--font-orbitron); font-size:0.75rem; color:#34d399; font-weight:900;">${card.hp ? card.hp + ' HP' : ''}</span>
                                </div>
                                <div style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:900; color:#fff; margin:4px 0;">${card.name}</div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                    <span style="font-size:0.7rem; color:var(--neon-cyan);">${card.pokemon_type || 'Colorless'}</span>
                                    <span class="cyber-badge" style="font-size:0.55rem; padding:2px 6px;">${card.rarity}</span>
                                </div>

                                <!-- Card Art with Fallback -->
                                <div style="position:relative; width:100%; height:110px; background:rgba(2,4,9,0.7); border-radius:6px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
                                    <img src="${card.image || ''}" alt="${card.name}" style="max-height:100px; object-fit:contain;"
                                         onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                                    <div style="display:none; width:100%; height:100%; flex-direction:column; align-items:center; justify-content:center; font-size:2rem;">
                                        ${card.card_type === 'pokemon' ? '🐉' : (card.card_type === 'energy' ? '⚡' : '🧰')}
                                    </div>
                                </div>

                                <div style="margin-top:6px; font-size:0.7rem; color:#cbd5e1; max-height:48px; overflow:hidden;">
                                    ${card.attacks && card.attacks[0] ? `<b>${card.attacks[0].name}</b>: ${card.attacks[0].base_damage || 0} DMG` : (card.effect || '')}
                                </div>
                            </div>
                            <div style="margin-top:6px; text-align:center;">
                                ${dupBadge}
                            </div>
                        </div>
                    </div>
                `;

                wrapper.onclick = () => flipCard(wrapper, idx);
                grid.appendChild(wrapper);
            });

            area.scrollIntoView({ behavior: 'smooth' });
        }

        function flipCard(wrapperEl, idx) {
            if (wrapperEl.classList.contains('flipped')) return;
            wrapperEl.classList.add('flipped');

            const countEl = document.getElementById('revealed-count');
            const current = parseInt(countEl.textContent || '0') + 1;
            countEl.textContent = current;

            if (current >= 8) {
                setTimeout(() => {
                    document.getElementById('pack-summary-dock').style.display = 'block';
                }, 600);
            }
        }

        function revealAllPackCards() {
            const wrappers = document.querySelectorAll('.card-flip-wrapper');
            wrappers.forEach((w, i) => {
                setTimeout(() => {
                    flipCard(w, i);
                }, i * 120);
            });
        }

        function getRarityClass(rarity) {
            switch ((rarity || '').toLowerCase()) {
                case 'uncommon': return 'rarity-uncommon';
                case 'rare': return 'rarity-rare';
                case 'ultra rare': return 'rarity-ultra-rare';
                case 'special': return 'rarity-special';
                default: return 'rarity-common';
            }
        }

        // ================= 4. COLLECTION MANAGEMENT =================
        async function loadUserCollection(updateView = true) {
            if (!AUTH_TOKEN) return;
            try {
                let url = `/api/v1/collection?category=${encodeURIComponent(FILTER_CATEGORY)}&stage=${encodeURIComponent(FILTER_STAGE)}&rarity=${encodeURIComponent(FILTER_RARITY)}`;
                if (SEARCH_QUERY) url += `&search=${encodeURIComponent(SEARCH_QUERY)}`;

                const res = await fetch(url, {
                    headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
                });
                const data = await res.json();
                if (data.status === 'success') {
                    OWNED_CARDS = data.cards || [];
                    OWNED_CARDS_MAP = {};
                    OWNED_CARDS.forEach(c => {
                        OWNED_CARDS_MAP[c.card_id] = c;
                        OWNED_CARDS_MAP[c.name.toLowerCase()] = c;
                    });
                    if (data.stats) updateCollectionStatsUI(data.stats);
                    if (updateView) renderOwnedCardsGrid();

                    if (CHOSEN_4_CARDS.length === 0 && OWNED_CARDS.length > 0) {
                        autoDealFromOwned(true);
                    }
                }
            } catch (err) {
                console.error("Failed to load collection:", err);
            }
        }

        function renderOwnedCardsGrid() {
            const grid = document.getElementById('owned-cards-grid');
            const emptyBox = document.getElementById('empty-collection-box');
            if (!grid) return;

            grid.innerHTML = '';

            if (OWNED_CARDS.length === 0) {
                if (emptyBox) emptyBox.style.display = 'block';
                return;
            } else {
                if (emptyBox) emptyBox.style.display = 'none';
            }

            OWNED_CARDS.forEach(card => {
                const isBasic = isBasicPokemon(card);
                const rarityClass = getRarityClass(card.rarity);
                const div = document.createElement('div');
                div.className = `owned-card-box ${rarityClass}`;

                div.innerHTML = `
                    <div class="qty-badge">×${card.quantity}</div>
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; padding-right:45px;">
                            <span style="font-family:var(--font-mono); font-size:0.65rem; color:var(--text-dim);">${card.card_type.toUpperCase()}</span>
                            <span style="font-family:var(--font-orbitron); font-size:0.8rem; font-weight:800; color:#34d399;">${card.hp ? card.hp + ' HP' : ''}</span>
                        </div>
                        <div style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:900; color:#fff; margin:4px 0;">${card.name}</div>
                        <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px;">
                            <span style="font-size:0.7rem; color:var(--neon-cyan);">${card.pokemon_type || 'Colorless'}</span>
                            <span class="cyber-badge" style="font-size:0.55rem; padding:2px 6px;">${card.rarity}</span>
                            ${card.stage ? `<span style="font-size:0.65rem; color:var(--neon-green); font-family:var(--font-mono);">[${card.stage}]</span>` : ''}
                        </div>

                        <!-- Image with fallback -->
                        <div style="position:relative; width:100%; height:110px; background:rgba(2,4,9,0.7); border-radius:6px; overflow:hidden; display:flex; align-items:center; justify-content:center; margin-bottom:8px;">
                            <img src="${card.image || ''}" alt="${card.name}" style="max-height:100px; object-fit:contain;"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                            <div style="display:none; width:100%; height:100%; flex-direction:column; align-items:center; justify-content:center; font-size:2.2rem;">
                                ${card.card_type === 'pokemon' ? '🐉' : (card.card_type === 'energy' ? '⚡' : '🧰')}
                            </div>
                        </div>

                        <div style="font-size:0.72rem; color:#cbd5e1; margin-bottom:8px;">
                            ${card.attacks && card.attacks[0] ? `⚔️ <b>${card.attacks[0].name}</b>: ${card.attacks[0].base_damage || 0} DMG` : (card.effect || '')}
                        </div>
                    </div>

                    <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px;">
                        <button class="btn-cyber-sm btn-add-deck" style="flex:1; padding:6px 8px; font-size:0.7rem; text-align:center; border-color:var(--neon-cyan); color:var(--neon-cyan);">
                            ➕ ADD TO DECK (<span class="card-in-deck-count">${getCardCountInCurrentDeck(card.card_id || card.name)}</span>/${card.quantity || 1})
                        </button>
                    </div>
                `;

                const btnAdd = div.querySelector('.btn-add-deck');
                if (btnAdd) btnAdd.onclick = () => addCardToCurrentDeck(card);

                grid.appendChild(div);
            });
        }

        function isBasicPokemon(c) {
            if (!c) return false;
            if (typeof c === 'string') {
                const meta = getCardMeta(c);
                return isBasicPokemon(meta);
            }
            const ctype = (c.card_type || c.supertype || '').toLowerCase();
            if (ctype && !ctype.includes('pok')) return false;
            if (c.stage === 'Basic') return true;
            if (c.stage === 'Stage 1' || c.stage === 'Stage 2') return false;
            const subs = (c.subtypes || []).map(s => s.toLowerCase());
            if (subs.includes('basic')) return true;
            if (subs.some(s => s.includes('stage'))) return false;
            return true;
        }

        // ================= FILTERS & SEARCH =================
        function setCategoryFilter(cat, btn) {
            FILTER_CATEGORY = cat;
            document.querySelectorAll('[data-filter-cat]').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            loadUserCollection();
        }

        function setStageFilter(stg, btn) {
            FILTER_STAGE = stg;
            document.querySelectorAll('[data-filter-stage]').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            loadUserCollection();
        }

        function setRarityFilter(rar, btn) {
            FILTER_RARITY = rar;
            document.querySelectorAll('[data-filter-rarity]').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            loadUserCollection();
        }

        function debounceFilterOwnedCards() {
            clearTimeout(filterDebounceTimer);
            filterDebounceTimer = setTimeout(() => {
                SEARCH_QUERY = document.getElementById('cards-search-input').value.trim();
                loadUserCollection();
            }, 250);
        }

        // ================= 5. 3-SLOT 60-CARD DECK BUILDER =================
        async function loadUserDecks() {
            // Load local storage cache first
            try {
                const localDecks = localStorage.getItem('pokemon_tcg_user_decks');
                if (localDecks) {
                    const parsed = JSON.parse(localDecks);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        USER_DECKS = parsed;
                        const activeDeck = USER_DECKS.find(d => d.is_active);
                        if (activeDeck) ACTIVE_DECK_SLOT = activeDeck.slot;
                        console.log(`[DECK BUILDER] Loaded ${USER_DECKS.length} decks from local storage. Active slot: ${ACTIVE_DECK_SLOT}`);
                    }
                }
            } catch(e) {
                console.warn("Could not parse local decks cache:", e);
            }

            if (AUTH_TOKEN) {
                try {
                    const res = await fetch('/api/v1/decks/user', {
                        headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.decks && data.decks.length > 0) {
                            USER_DECKS = data.decks;
                            const activeDeck = USER_DECKS.find(d => d.is_active);
                            if (activeDeck) ACTIVE_DECK_SLOT = activeDeck.slot;
                            localStorage.setItem('pokemon_tcg_user_decks', JSON.stringify(USER_DECKS));
                        }
                    }
                } catch(e) {
                    console.warn("Notice: Offline deck builder state used", e);
                }
            }

            // Clean up any previously injected starter lines if user has other cards (e.g. Glameow, Mr. Mime ex, Munchlax)
            const injectedStarters = ["Pikachu", "Raichu", "Charmander", "Charmeleon", "Charizard", "Squirtle", "Wartortle", "Blastoise", "Bulbasaur", "Ivysaur", "Venusaur"];
            const stapleTrainers = ["Potion", "Switch", "Ultra Ball", "Professor's Research", "Nest Ball", "Boss's Orders"];
            USER_DECKS.forEach(deck => {
                if (deck.cards && deck.cards.length > 0) {
                    const hasUserCards = deck.cards.some(c => !injectedStarters.includes(c) && !c.toLowerCase().includes('energy') && !stapleTrainers.includes(c));
                    if (hasUserCards) {
                        // User chose their own Pokémon: strip out all auto-injected starters and trainers!
                        deck.cards = deck.cards.filter(c => !injectedStarters.includes(c) && !stapleTrainers.includes(c) && !c.toLowerCase().includes('item energy'));
                    }
                }
            });
            try {
                localStorage.setItem('pokemon_tcg_user_decks', JSON.stringify(USER_DECKS));
            } catch(e) {}

            updateDeckTrayUI();
        }

        function getCurrentDeck() {
            let d = USER_DECKS.find(x => x.slot === ACTIVE_DECK_SLOT);
            if (!d) {
                d = { slot: ACTIVE_DECK_SLOT, name: `My Deck ${ACTIVE_DECK_SLOT}`, cards: [], is_active: ACTIVE_DECK_SLOT === 1 ? 1 : 0 };
                USER_DECKS.push(d);
            }
            return d;
        }

        function switchDeckSlot(slot) {
            ACTIVE_DECK_SLOT = slot;
            [1, 2, 3].forEach(s => {
                const btn = document.getElementById(`deck-tab-${s}`);
                if (btn) {
                    if (s === slot) btn.classList.add('active');
                    else btn.classList.remove('active');
                }
            });
            const cur = getCurrentDeck();
            const nameInput = document.getElementById('deck-name-input');
            if (nameInput) nameInput.value = cur.name || `My Deck ${slot}`;
            updateDeckTrayUI();
        }

        function updateCurrentDeckName(name) {
            const cur = getCurrentDeck();
            cur.name = name.trim() || `My Deck ${ACTIVE_DECK_SLOT}`;
            const tab = document.getElementById(`deck-tab-${ACTIVE_DECK_SLOT}`);
            if (tab) tab.innerHTML = `${cur.name} (<span id="deck-count-tab-${ACTIVE_DECK_SLOT}">${(cur.cards || []).length}</span>/60)`;
        }

        function getCardCountInCurrentDeck(cardIdentifier) {
            const cur = getCurrentDeck();
            if (!cur.cards) return 0;
            const targetId = typeof cardIdentifier === 'object' && cardIdentifier !== null
                ? String(cardIdentifier.card_id || cardIdentifier.name).trim().toLowerCase()
                : String(cardIdentifier).trim().toLowerCase();
            return cur.cards.filter(c => {
                const cId = typeof c === 'object' && c !== null ? String(c.card_id || c.name).trim().toLowerCase() : String(c).trim().toLowerCase();
                if (cId === targetId) return true;
                const meta = getCardMeta(c);
                if (meta && meta.name && meta.name.toLowerCase() === targetId) return true;
                if (meta && meta.card_id && String(meta.card_id).trim().toLowerCase() === targetId) return true;
                return false;
            }).length;
        }

        function addCardToCurrentDeck(cardItem) {
            const cur = getCurrentDeck();
            if (!cur.cards) cur.cards = [];
            if (cur.cards.length >= 60) {
                alert("⚠️ Deck is full (maximum 60 cards allowed per standard rules)! Remove cards before adding more.");
                return;
            }
            const meta = getCardMeta(cardItem);
            const cardIdOrName = (meta && meta.card_id) ? String(meta.card_id).trim() : (typeof cardItem === 'string' ? cardItem : (cardItem.card_id || cardItem.name));
            const countInDeck = getCardCountInCurrentDeck(cardIdOrName);
            const isEnergy = (meta.card_type === 'energy' || (meta.name && meta.name.toLowerCase().includes('energy')));
            if (!isEnergy && meta.quantity && countInDeck >= meta.quantity) {
                alert(`⚠️ You only own ${meta.quantity} copy of '${meta.name || cardIdOrName}'! Open booster packs to collect more.`);
                return;
            }
            cur.cards.push(cardIdOrName);
            console.log(`[DECK] Added card to deck ${cur.slot}:`, cardIdOrName, `(Total: ${cur.cards.length}/60)`);
            updateDeckTrayUI();
        }

        function removeCardFromCurrentDeck(index) {
            const cur = getCurrentDeck();
            if (cur.cards && cur.cards.length > index) {
                cur.cards.splice(index, 1);
                updateDeckTrayUI();
            }
        }

        function clearCurrentDeck() {
            const cur = getCurrentDeck();
            if (confirm(`Are you sure you want to remove all cards from '${cur.name}'?`)) {
                cur.cards = [];
                updateDeckTrayUI();
            }
        }

        function balanceDeckList(existingCards = []) {
            const newDeck = [...(existingCards || [])];
            if (newDeck.length === 0) {
                return ["Pikachu", "Pikachu", "Raichu", "Charmander", "Charmander", "Potion", "Switch", "Basic Lightning Energy", "Basic Fire Energy"];
            }

            // Determine types of user's chosen Pokémon
            const types = new Set();
            newDeck.forEach(c => {
                const m = getCardMeta(c);
                if (m && m.pokemon_type && m.pokemon_type !== "Colorless") types.add(m.pokemon_type);
            });
            const validTypes = Array.from(types);
            if (validTypes.length === 0) validTypes.push("Psychic", "Fire");

            // Fill remaining slots with Basic Energy matching the user's chosen Pokémon types
            let eIdx = 0;
            while (newDeck.length < 60) {
                const etype = validTypes[eIdx % validTypes.length];
                newDeck.push(`Basic ${etype} Energy`);
                eIdx++;
            }
            return newDeck.slice(0, 60);
        }

        function autoCompleteBalancedDeck() {
            const cur = getCurrentDeck();
            if (!cur.cards) cur.cards = [];
            cur.cards = balanceDeckList(cur.cards);
            updateDeckTrayUI();
            try {
                localStorage.setItem('pokemon_tcg_user_decks', JSON.stringify(USER_DECKS));
            } catch(e) {}
            console.log(`[DECK BUILDER] Auto-completed deck with matching energy for Slot ${cur.slot}: ${cur.cards.length} cards`);
        }

        function autoFillDeckWithEnergy() {
            autoCompleteBalancedDeck();
        }

        function showDeckBuilderEmptyPrompt() {
            const banner = document.getElementById('empty-deck-alert-banner');
            if (banner) {
                banner.style.display = 'block';
                banner.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }

        function hideDeckBuilderEmptyPrompt() {
            const banner = document.getElementById('empty-deck-alert-banner');
            if (banner) banner.style.display = 'none';
        }

        async function quickAutoFillAndStartBattle() {
            autoCompleteBalancedDeck();
            await saveAndStartBattle();
        }

        async function saveAndStartBattle() {
            const cur = getCurrentDeck();
            if (!cur.cards || cur.cards.length === 0) {
                alert("⚠️ Please add cards to your deck before starting battle!");
                return;
            }
            await saveCurrentDeckSlot(true);
            await selectCurrentDeckForBattle(true);
            hideDeckBuilderEmptyPrompt();
            switchMode('match');
            await startNewMatch(false, true);
        }

        async function saveCurrentDeckSlot(quiet = false) {
            const cur = getCurrentDeck();
            try {
                localStorage.setItem('pokemon_tcg_user_decks', JSON.stringify(USER_DECKS));
            } catch(e) {}
            console.log(`[DECK BUILDER] Saved deck ID: Slot ${cur.slot} | name: "${cur.name}" | count: ${(cur.cards || []).length}/60`);

            if (AUTH_TOKEN) {
                try {
                    const res = await fetch('/api/v1/decks/user/save', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${AUTH_TOKEN}`
                        },
                        body: JSON.stringify({
                            slot: cur.slot,
                            name: cur.name,
                            cards: cur.cards || [],
                            is_active: cur.is_active || 0
                        })
                    });
                    const data = await res.json();
                    if (!quiet) {
                        if (res.ok && data.status === 'success') {
                            alert(`✅ Deck '${cur.name}' saved successfully! (${(cur.cards || []).length}/60 cards)`);
                        } else {
                            alert(`💾 Saved locally (${(cur.cards || []).length}/60 cards)`);
                        }
                    }
                } catch(e) {
                    if (!quiet) alert(`💾 Saved locally (${(cur.cards || []).length}/60 cards)`);
                }
            } else {
                if (!quiet) alert(`💾 Saved locally (${(cur.cards || []).length}/60 cards)`);
            }
            updateDeckTrayUI();
        }

        async function selectCurrentDeckForBattle(quiet = false) {
            const cur = getCurrentDeck();
            if (!cur.cards || cur.cards.length === 0) {
                if (!quiet) alert("⚠️ Cannot select an empty deck for battle! Add cards to your deck first.");
                return;
            }
            USER_DECKS.forEach(d => { d.is_active = (d.slot === cur.slot) ? 1 : 0; });
            try {
                localStorage.setItem('pokemon_tcg_user_decks', JSON.stringify(USER_DECKS));
            } catch(e) {}
            if (AUTH_TOKEN) {
                try {
                    await fetch('/api/v1/decks/user/select', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${AUTH_TOKEN}`
                        },
                        body: JSON.stringify({ slot: cur.slot })
                    });
                } catch(e) {}
            }
            console.log(`[SELECT DECK] Selected deck ID: Slot ${cur.slot} | name: "${cur.name}" | count: ${cur.cards.length}/60`);
            if (!quiet) alert(`⚔️ Deck '${cur.name}' is now your Active Battle Deck!`);
            updateDeckTrayUI();
        }

        async function startBattleWithCurrentDeck() {
            const cur = getCurrentDeck();
            if (!cur.cards || cur.cards.length === 0) {
                switchMode('cards');
                showDeckBuilderEmptyPrompt();
                return;
            }
            await selectCurrentDeckForBattle(true);
            hideDeckBuilderEmptyPrompt();
            switchMode('match');
            await startNewMatch(false, true);
        }

        function updateDeckTrayUI() {
            USER_DECKS.forEach(d => {
                const countTab = document.getElementById(`deck-count-tab-${d.slot}`);
                if (countTab) countTab.textContent = (d.cards || []).length;
            });

            const cur = getCurrentDeck();
            const count = (cur.cards || []).length;
            const countEl = document.getElementById('deck-cards-count');
            if (countEl) countEl.textContent = count;

            const badge = document.getElementById('active-deck-badge');
            if (badge) {
                if (cur.is_active) {
                    badge.style.display = 'inline-flex';
                    badge.textContent = 'ACTIVE BATTLE DECK';
                    badge.style.borderColor = 'var(--neon-green)';
                    badge.style.color = 'var(--neon-green)';
                } else {
                    badge.style.display = 'inline-flex';
                    badge.textContent = 'INACTIVE DECK';
                    badge.style.borderColor = 'var(--text-dim)';
                    badge.style.color = 'var(--text-dim)';
                }
            }

            const tray = document.getElementById('deck-cards-tray');
            if (tray) {
                if (!cur.cards || cur.cards.length === 0) {
                    tray.innerHTML = `<div style="color:var(--text-dim); font-size:0.75rem; font-style:italic; width:100%; text-align:center; padding:10px 0;">This deck is empty. Click "+ ADD TO DECK" on any card below to add up to 60 cards.</div>`;
                } else {
                    tray.innerHTML = cur.cards.map((cname, idx) => {
                        const meta = getCardMeta(cname);
                        const displayName = meta.name || meta.card_name || cname;
                        const isPkmn = meta.card_type === 'pokemon';
                        const color = isPkmn ? 'var(--neon-cyan)' : (meta.card_type === 'energy' ? 'var(--neon-amber)' : 'var(--neon-purple)');
                        return `
                            <div style="background:rgba(8,14,28,0.9); border:1px solid ${color}; border-radius:4px; padding:3px 8px; font-size:0.72rem; display:inline-flex; align-items:center; gap:6px;">
                                <span style="color:#fff; font-weight:700;">${displayName}</span>
                                <button style="background:none; border:none; color:#ef4444; font-size:0.8rem; font-weight:900; cursor:pointer; padding:0 2px;" onclick="removeCardFromCurrentDeck(${idx})" title="Remove">✕</button>
                            </div>
                        `;
                    }).join('');
                }
            }

            document.querySelectorAll('.owned-card-box').forEach(el => {
                const titleEl = el.querySelector('div[style*="font-family:var(--font-orbitron)"]');
                if (titleEl) {
                    const cardName = titleEl.textContent.trim();
                    const counterEl = el.querySelector('.card-in-deck-count');
                    if (counterEl) {
                        counterEl.textContent = getCardCountInCurrentDeck(cardName);
                    }
                }
            });
        }

        function getCardMeta(cname) {
            if (!cname) return { name: "Unknown", card_type: "pokemon", stage: "Basic", hp: 70, pokemon_type: "Normal", attacks: [] };
            if (typeof cname === 'object' && cname !== null) {
                if (cname.card_id && ALL_CARDS_MAP[String(cname.card_id).trim()]) return ALL_CARDS_MAP[String(cname.card_id).trim()];
                if (cname.name && ALL_CARDS_MAP[String(cname.name).toLowerCase().trim()]) return ALL_CARDS_MAP[String(cname.name).toLowerCase().trim()];
                return cname;
            }
            const identStr = String(cname).trim();
            const clean = identStr.toLowerCase();
            if (ALL_CARDS_MAP[identStr]) return ALL_CARDS_MAP[identStr];
            if (ALL_CARDS_MAP[clean]) return ALL_CARDS_MAP[clean];
            if (OWNED_CARDS_MAP[identStr]) return OWNED_CARDS_MAP[identStr];
            if (OWNED_CARDS_MAP[clean]) return OWNED_CARDS_MAP[clean];

            if (clean.includes('energy')) {
                return { name: cname, card_name: cname, card_type: "energy", supertype: "Energy", stage: "", image: "/static/card_images/placeholder_energy.svg" };
            }
            if (clean.includes('potion') || clean.includes('ball') || clean.includes('switch') || clean.includes('rope')) {
                return { name: cname, card_name: cname, card_type: "trainer", supertype: "Trainer", stage: "", image: "/static/card_images/placeholder_item.svg" };
            }
            if (clean.includes('research') || clean.includes('boss') || clean.includes('trainer') || clean.includes('supporter') || clean.includes('iono')) {
                return { name: cname, card_name: cname, card_type: "trainer", supertype: "Trainer", stage: "", image: "/static/card_images/placeholder_supporter.svg" };
            }
            return {
                name: cname,
                card_name: cname,
                card_type: "pokemon",
                stage: "Basic",
                subtypes: ["Basic"],
                hp: 70,
                pokemon_type: "Colorless",
                attacks: [{ name: "Strike", base_damage: 30, cost: ["Colorless"] }],
                image: "/static/card_images/placeholder_pokemon.svg"
            };
        }

        async function startBattleWithSelected4Cards() {
            startNewMatch();
            switchMode('match');
        }

        // ================= 6. MATCH ARENA SIMULATION (60-CARD ENGINE) =================
        function getMatchHeaders() {
            const headers = {
                'Content-Type': 'application/json',
                'X-API-Key': 'tcg-live-secret-key-2026'
            };
            if (AUTH_TOKEN) headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
            return headers;
        }

        function buildOwned60CardDeck(baseList = []) {
            if (!baseList || baseList.length === 0) {
                return fisherYatesShuffle(["Pikachu", "Pikachu", "Raichu", "Charmander", "Charmander", "Potion", "Switch", "Basic Lightning Energy", "Basic Fire Energy"]);
            }
            // Preserve EXACT cards chosen by the user! Decks can be less than 60 cards!
            return fisherYatesShuffle([...baseList]);
        }

        function buildOpponent60CardDeck() {
            // 100% Rule-Compliant Random Opponent Deck Generation:
            // - Exactly 60 cards total
            // - Rule of 4: Max 4 copies of any non-energy card
            // - Valid Basic -> Evolution lines
            // - Basic Energies matching Pokémon types
            // - Authentic items and supporters
            const families = [
                { type: "Fire", cards: [["Charmander", 3], ["Charmeleon", 2], ["Charizard", 2]] },
                { type: "Fire", cards: [["Charmander", 3], ["Charmeleon", 2]] },
                { type: "Lightning", cards: [["Pikachu", 3], ["Raichu", 2], ["Pikachu ex", 2]] },
                { type: "Lightning", cards: [["Pikachu", 4], ["Raichu", 2]] },
                { type: "Water", cards: [["Squirtle", 3], ["Wartortle", 2], ["Blastoise", 2]] },
                { type: "Water", cards: [["Squirtle", 4], ["Wartortle", 2]] },
                { type: "Grass", cards: [["Bulbasaur", 3], ["Ivysaur", 2], ["Venusaur", 2]] },
                { type: "Grass", cards: [["Bulbasaur", 4], ["Ivysaur", 2]] },
                { type: "Psychic", cards: [["Ralts", 3], ["Kirlia", 2], ["Gardevoir", 2]] },
                { type: "Fighting", cards: [["Machop", 3], ["Machoke", 2], ["Machamp", 2]] },
                { type: "Darkness", cards: [["Houndour", 3], ["Houndoom", 2]] }
            ];
            const standaloneBasics = [
                { type: "Lightning", name: "Zapdos", count: 2 },
                { type: "Water", name: "Lapras", count: 2 },
                { type: "Colorless", name: "Snorlax", count: 2 },
                { type: "Colorless", name: "Eevee", count: 3 },
                { type: "Colorless", name: "Tauros", count: 2 },
                { type: "Psychic", name: "Mewtwo", count: 2 }
            ];

            const deck = [];
            const chosenTypes = new Set();

            // Randomly select 2 distinct families
            const shuffledFamilies = fisherYatesShuffle(families);
            const fam1 = shuffledFamilies[0];
            const fam2 = shuffledFamilies[1];
            chosenTypes.add(fam1.type);
            chosenTypes.add(fam2.type);

            fam1.cards.forEach(([name, cnt]) => {
                for (let i = 0; i < cnt; i++) deck.push(name);
            });
            fam2.cards.forEach(([name, cnt]) => {
                for (let i = 0; i < cnt; i++) deck.push(name);
            });

            // Randomly select 1 standalone basic
            const basicObj = standaloneBasics[Math.floor(Math.random() * standaloneBasics.length)];
            chosenTypes.add(basicObj.type);
            for (let i = 0; i < basicObj.count; i++) deck.push(basicObj.name);

            // Add Trainers (max 4 per card)
            const trainerPool = ["Potion", "Switch", "Poké Ball", "Ultra Ball", "Professor's Research", "Boss's Orders", "Rare Candy", "Super Rod", "Nest Ball", "Energy Retrieval"];
            const shuffledTrainers = fisherYatesShuffle(trainerPool);
            let tIdx = 0;
            const trainerCounts = {};
            while (deck.length < 60 - 15) { // Leave ~15 slots for energy
                const t = shuffledTrainers[tIdx % shuffledTrainers.length];
                trainerCounts[t] = (trainerCounts[t] || 0) + 1;
                if (trainerCounts[t] <= 4) {
                    deck.push(t);
                }
                tIdx++;
            }

            // Add Energies matching chosen types
            const validTypes = Array.from(chosenTypes).filter(t => t !== "Colorless");
            if (validTypes.length === 0) validTypes.push("Lightning", "Fire");
            let eIdx = 0;
            while (deck.length < 60) {
                const etype = validTypes[eIdx % validTypes.length];
                deck.push(`Basic ${etype} Energy`);
                eIdx++;
            }

            return fisherYatesShuffle(deck);
        }

        function fisherYatesShuffle(arr) {
            const a = [...arr];
            for (let i = a.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [a[i], a[j]] = [a[j], a[i]];
            }
            return a;
        }

        async function startNewMatch(keepPlayerCards = false, deckExplicitlyReady = false) {
            SELECTED_CARD_KEY = null;
            SELECTED_CARD_ID = null;
            SELECTED_CARD_DATA = null;

            const activeDeckObj = USER_DECKS.find(d => d.is_active) || USER_DECKS[0];
            const slotNum = activeDeckObj ? activeDeckObj.slot : ACTIVE_DECK_SLOT;
            const customCards = (activeDeckObj && activeDeckObj.cards && activeDeckObj.cards.length > 0) ? activeDeckObj.cards : null;

            if (!deckExplicitlyReady && (!customCards || customCards.length === 0)) {
                console.log("[START BATTLE] Active deck is empty! Directing to Deck Builder to create deck first.");
                switchMode('cards');
                showDeckBuilderEmptyPrompt();
                return;
            }

            console.log(`[START BATTLE] Starting battle with selected deck ID: Slot ${slotNum} ("${activeDeckObj ? activeDeckObj.name : 'Deck'}") | Cards count: ${customCards ? customCards.length : 'default'}`);

            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/start', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        deck_slot: slotNum,
                        custom_deck_list: customCards,
                        player_deck_id: "charizard-fire",
                        opp_deck_id: "random"
                    })
                });
                if (res.ok) {
                    const data = await res.json();
                    CURRENT_MATCH_STATE = data.match_state;
                    console.log("[SHUFFLE] Player and AI 60-card decks shuffled.");
                    const remainingDeck = (CURRENT_MATCH_STATE.player && (CURRENT_MATCH_STATE.player.deck_count !== undefined ? CURRENT_MATCH_STATE.player.deck_count : (CURRENT_MATCH_STATE.player.deck || []).length)) || 49;
                    console.log(`[INITIAL DRAW] 5 cards dealt to Player hand. Face-down deck remaining: ${remainingDeck} cards.`);
                    updateMatchView(CURRENT_MATCH_STATE);
                    if (data.ai_recommendation) {
                        LAST_AI_REPORT = data.ai_recommendation;
                        renderStrategicAiReport(data.ai_recommendation);
                    }
                    return;
                }
            } catch (err) {
                console.warn("[MATCH] Backend match/start call failed, fallback locally:", err);
            }

            // Local fallback maintaining exact selected deck
            let pDeck = buildOwned60CardDeck(customCards || []);
            let oppDeck = buildOpponent60CardDeck();
            console.log(`[SHUFFLE] Shuffled player deck (${pDeck.length} cards) and AI deck (${oppDeck.length} cards).`);

            // Setup Prize cards (scaled if deck has fewer than 25 cards)
            const pPrizeCount = pDeck.length < 25 ? Math.max(1, Math.min(6, Math.floor(pDeck.length / 4))) : 6;
            const pPrizes = [];
            for (let i = 0; i < pPrizeCount && pDeck.length > 0; i++) {
                pPrizes.push(pDeck.pop());
            }

            // SETUP HAND:
            // "in hand the deck cards in the are able to select for main and bench if the card is not able to set in main or bench that card should not in the hand"
            // Only Basic Pokémon eligible to be placed in Main or Bench are drawn into the setup hand!
            const pHand = [];
            const basicIndices = [];
            for (let i = 0; i < pDeck.length; i++) {
                if (isBasicPokemon(getCardMeta(pDeck[i]))) {
                    basicIndices.push(i);
                }
            }
            const setupCount = Math.min(5, basicIndices.length);
            for (let k = 0; k < setupCount; k++) {
                const bIdx = pDeck.findIndex(c => isBasicPokemon(getCardMeta(c)));
                if (bIdx !== -1) {
                    pHand.push(pDeck.splice(bIdx, 1)[0]);
                }
            }
            // Fallback if deck has 0 basic pokemon
            if (pHand.length === 0 && pDeck.length > 0) {
                pHand.push(pDeck.pop());
            }

            let oppHand = [oppDeck.pop(), oppDeck.pop(), oppDeck.pop(), oppDeck.pop(), oppDeck.pop()];
            let oppMulligan = 0;
            while (!oppHand.some(c => isBasicPokemon(getCardMeta(c))) && oppMulligan < 30 && oppDeck.length > 0) {
                oppMulligan++;
                oppDeck.push(...oppHand);
                oppDeck = fisherYatesShuffle(oppDeck);
                oppHand = [oppDeck.pop(), oppDeck.pop(), oppDeck.pop(), oppDeck.pop(), oppDeck.pop()];
            }
            console.log(`[SETUP DRAW] ${pHand.length} Basic Pokémon dealt to setup hand. Face-down deck remaining: ${pDeck.length} cards.`);

            CURRENT_ROUTE_STEP_INDEX = 0;
            CURRENT_MATCH_STATE = {
                turn_number: 1,
                phase: 'SETUP',
                is_player_turn: true,
                card_drawn_this_turn: false,
                energy_attached_this_turn: false,
                winner: null,
                player: {
                    name: CURRENT_USER ? CURRENT_USER.username : "Player",
                    active_spot: null,
                    bench: [],
                    hand: pHand,
                    deck: pDeck,
                    discard: [],
                    prizes_taken: 0
                },
                opponent: {
                    name: "Opponent AI",
                    active_spot: null,
                    bench: [],
                    hand: oppHand,
                    deck: oppDeck,
                    discard: [],
                    prizes_taken: 0
                },
                match_log: [
                    "⚔️ 60-Card Match Arena initialized!",
                    `🎯 SETUP PHASE: You drew 5 opening cards (${pDeck.length} cards left in your face-down deck).`,
                    "Select 1 Basic Pokémon from your hand for Active Spot, and up to 3 for Bench Slots.",
                    "If your opening hand has no Basic Pokémon, click [MULLIGAN REDRAW]."
                ]
            };
            updateMatchView(CURRENT_MATCH_STATE);
        }

        async function triggerMulligan() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.phase !== 'SETUP') return;
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/mulligan', { method: 'POST', headers: headers });
                if (res.ok) {
                    const data = await res.json();
                    if (data.result && data.result.status === 'error') {
                        alert(`⚠️ ${data.result.message}`);
                        return;
                    }
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    return;
                }
            } catch(e) {
                console.warn("Mulligan API call fallback:", e);
            }

            const hand = CURRENT_MATCH_STATE.player.hand || [];
            const hasBasic = hand.some(c => isBasicPokemon(getCardMeta(c)));
            if (hasBasic) {
                if (!confirm("⚠️ You have Basic Pokémon in your hand! Standard TCG rules only permit Mulligan when no Basic Pokémon are present. Redraw anyway?")) {
                    return;
                }
            }
            CURRENT_MATCH_STATE.player.deck.push(...hand);
            CURRENT_MATCH_STATE.player.deck = fisherYatesShuffle(CURRENT_MATCH_STATE.player.deck);
            CURRENT_MATCH_STATE.player.hand = [
                CURRENT_MATCH_STATE.player.deck.pop(),
                CURRENT_MATCH_STATE.player.deck.pop(),
                CURRENT_MATCH_STATE.player.deck.pop(),
                CURRENT_MATCH_STATE.player.deck.pop(),
                CURRENT_MATCH_STATE.player.deck.pop()
            ];
            if (!CURRENT_MATCH_STATE.player.hand.some(c => isBasicPokemon(getCardMeta(c)))) {
                const bIdx = CURRENT_MATCH_STATE.player.deck.findIndex(c => isBasicPokemon(getCardMeta(c)));
                if (bIdx !== -1) {
                    CURRENT_MATCH_STATE.player.hand[0] = CURRENT_MATCH_STATE.player.deck.splice(bIdx, 1)[0];
                }
            }
            CURRENT_MATCH_STATE.match_log.push("🔄 Mulligan Redraw: Shuffled hand back into 60-card deck and drew 5 new cards.");
            updateMatchView(CURRENT_MATCH_STATE);
        }

        async function setupPlaceActive(cname) {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.phase !== 'SETUP') return;
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/place-and-battle', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ card_name: cname, slot: "active" })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.result && data.result.status === 'error') {
                        if (data.result.message && data.result.message.includes("is not in your hand")) {
                            console.warn("State desync detected. Refreshing hand from server state.");
                            if (data.match_state) {
                                CURRENT_MATCH_STATE = data.match_state;
                                updateMatchView(CURRENT_MATCH_STATE);
                            }
                        }
                        alert(`❌ ${data.result.message}`);
                        return;
                    }
                    SELECTED_CARD_KEY = null;
                    SELECTED_CARD_ID = null;
                    SELECTED_CARD_DATA = null;
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    runDynamicAiAnalysis(CURRENT_MATCH_STATE);
                    return;
                }
            } catch(e) {
                console.warn("setupPlaceActive API fallback:", e);
            }

            const meta = getCardMeta(cname);
            if (!isBasicPokemon(meta)) {
                alert(`❌ Invalid Selection: '${cname}' is a ${meta.stage || 'Stage 1/2'} Pokémon! Only Basic Pokémon can be placed during setup.`);
                return;
            }
            const idx = CURRENT_MATCH_STATE.player.hand.findIndex(c => {
                if (!c) return false;
                const n = typeof c === 'string' ? c : (c.name || c.card_name);
                const cid = typeof c === 'object' ? c.card_id : null;
                return n === cname || String(cid) === String(cname);
            });
            if (idx === -1) return;
            SELECTED_CARD_KEY = null;
            SELECTED_CARD_ID = null;
            SELECTED_CARD_DATA = null;
            CURRENT_MATCH_STATE.player.hand.splice(idx, 1);
            CURRENT_MATCH_STATE.player.active_spot = {
                name: cname,
                current_hp: meta.hp || 70,
                max_hp: meta.hp || 70,
                attached_energy: [],
                image: meta.image || getCardImageUrl(meta, cname)
            };
            // Place any remaining Basic Pokémon in hand onto empty bench slots
            for (let i = CURRENT_MATCH_STATE.player.hand.length - 1; i >= 0; i--) {
                const cand = CURRENT_MATCH_STATE.player.hand[i];
                const candName = typeof cand === 'string' ? cand : (cand.name || cand.card_name);
                const candMeta = getCardMeta(candName);
                if (isBasicPokemon(candMeta) && (CURRENT_MATCH_STATE.player.bench || []).length < 3) {
                    CURRENT_MATCH_STATE.player.hand.splice(i, 1);
                    CURRENT_MATCH_STATE.player.bench.push({
                        name: candName,
                        current_hp: candMeta.hp || 70,
                        max_hp: candMeta.hp || 70,
                        attached_energy: [],
                        image: candMeta.image || getCardImageUrl(candMeta, candName)
                    });
                }
            }
            CURRENT_MATCH_STATE.phase = 'BATTLE';
            while ((CURRENT_MATCH_STATE.player.hand || []).length < 5 && (CURRENT_MATCH_STATE.player.deck || []).length > 0) {
                CURRENT_MATCH_STATE.player.hand.push(CURRENT_MATCH_STATE.player.deck.pop());
            }
            CURRENT_MATCH_STATE.match_log.push(`👑 Placed [${cname}] into Active Spot and started battle!`);
            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        async function setupPlaceBench(cname) {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.phase !== 'SETUP') return;
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/place-and-battle', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ card_name: cname, slot: "bench" })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.result && data.result.status === 'error') {
                        if (data.result.message && data.result.message.includes("is not in your hand")) {
                            console.warn("State desync detected. Refreshing hand from server state.");
                            if (data.match_state) {
                                CURRENT_MATCH_STATE = data.match_state;
                                updateMatchView(CURRENT_MATCH_STATE);
                            }
                        }
                        alert(`❌ ${data.result.message}`);
                        return;
                    }
                    SELECTED_CARD_KEY = null;
                    SELECTED_CARD_ID = null;
                    SELECTED_CARD_DATA = null;
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    runDynamicAiAnalysis(CURRENT_MATCH_STATE);
                    return;
                }
            } catch(e) {
                console.warn("setupPlaceBench API fallback:", e);
            }

            const meta = getCardMeta(cname);
            if (!isBasicPokemon(meta)) {
                alert(`❌ Invalid Selection: '${cname}' is a ${meta.stage || 'Stage 1/2'} Pokémon! Only Basic Pokémon can be placed during setup.`);
                return;
            }
            const idx = CURRENT_MATCH_STATE.player.hand.findIndex(c => {
                if (!c) return false;
                const n = typeof c === 'string' ? c : (c.name || c.card_name);
                const cid = typeof c === 'object' ? c.card_id : null;
                return n === cname || String(cid) === String(cname);
            });
            if (idx === -1) return;
            SELECTED_CARD_KEY = null;
            SELECTED_CARD_ID = null;
            SELECTED_CARD_DATA = null;
            CURRENT_MATCH_STATE.player.hand.splice(idx, 1);
            CURRENT_MATCH_STATE.player.bench.push({
                name: cname,
                current_hp: meta.hp || 70,
                max_hp: meta.hp || 70,
                attached_energy: [],
                image: meta.image || getCardImageUrl(meta, cname)
            });
            // If active spot is empty, place another basic or promote this one
            if (!CURRENT_MATCH_STATE.player.active_spot) {
                const bIdx = CURRENT_MATCH_STATE.player.hand.findIndex(c => isBasicPokemon(getCardMeta(typeof c === 'string' ? c : (c.name || c.card_name))));
                if (bIdx !== -1) {
                    const actCard = CURRENT_MATCH_STATE.player.hand.splice(bIdx, 1)[0];
                    const actName = typeof actCard === 'string' ? actCard : (actCard.name || actCard.card_name);
                    const actMeta = getCardMeta(actName);
                    CURRENT_MATCH_STATE.player.active_spot = {
                        name: actName,
                        current_hp: actMeta.hp || 70,
                        max_hp: actMeta.hp || 70,
                        attached_energy: [],
                        image: actMeta.image || getCardImageUrl(actMeta, actName)
                    };
                } else {
                    CURRENT_MATCH_STATE.player.active_spot = CURRENT_MATCH_STATE.player.bench.pop();
                }
            }
            CURRENT_MATCH_STATE.phase = 'BATTLE';
            while ((CURRENT_MATCH_STATE.player.hand || []).length < 5 && (CURRENT_MATCH_STATE.player.deck || []).length > 0) {
                CURRENT_MATCH_STATE.player.hand.push(CURRENT_MATCH_STATE.player.deck.pop());
            }
            CURRENT_MATCH_STATE.match_log.push(`🛡️ Placed [${cname}] into Bench and started battle!`);
            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        async function confirmInitialSetup() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.phase !== 'SETUP') return;
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/confirm-setup', { method: 'POST', headers: headers });
                if (res.ok) {
                    const data = await res.json();
                    if (data.result && data.result.status === 'error') {
                        alert(`⚠️ ${data.result.message}`);
                        return;
                    }
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    runDynamicAiAnalysis(CURRENT_MATCH_STATE);
                    return;
                }
            } catch(e) {
                console.warn("confirmInitialSetup API fallback:", e);
            }

            if (!CURRENT_MATCH_STATE.player.active_spot) {
                alert("⚠️ You must place 1 Basic Pokémon into the Active Spot before confirming setup!");
                return;
            }
            CURRENT_MATCH_STATE.phase = 'BATTLE';
            // Draw opening battle hand (up to 5 cards) from the deck
            while ((CURRENT_MATCH_STATE.player.hand || []).length < 5 && (CURRENT_MATCH_STATE.player.deck || []).length > 0) {
                CURRENT_MATCH_STATE.player.hand.push(CURRENT_MATCH_STATE.player.deck.pop());
            }
            CURRENT_MATCH_STATE.match_log.push("⚡ Setup confirmed! Turn 1 begins.");
            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        async function applyAiSetupRecommendation() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.phase !== 'SETUP') return;
            const hand = CURRENT_MATCH_STATE.player_hand_cards || (CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.hand) || [];
            const aiRec = getAiSetupRecommendations(hand);

            if (aiRec && aiRec.recommended_main) {
                if (!CURRENT_MATCH_STATE.player.active_spot) {
                    await setupPlaceActive(aiRec.recommended_main.card_name);
                }
                if (aiRec.recommended_bench && Array.isArray(aiRec.recommended_bench)) {
                    for (let b of aiRec.recommended_bench) {
                        const currBench = CURRENT_MATCH_STATE.player.bench || [];
                        if (currBench.length < 3) {
                            await setupPlaceBench(b.card_name);
                        }
                    }
                }
            } else {
                for (let c of hand) {
                    const cname = typeof c === 'string' ? c : (c.name || c.card_name);
                    const meta = getCardMeta(cname);
                    if (isBasicPokemon(meta)) {
                        if (!CURRENT_MATCH_STATE.player.active_spot) {
                            await setupPlaceActive(cname);
                        } else if ((CURRENT_MATCH_STATE.player.bench || []).length < 3) {
                            await setupPlaceBench(cname);
                        }
                    }
                }
            }
        }

        async function autoPlaceSetupAndBattle() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.phase !== 'SETUP') return;
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/auto-place', {
                    method: 'POST',
                    headers: headers
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'success' || (data.result && data.result.status === 'success')) {
                        SELECTED_CARD_KEY = null;
                        SELECTED_CARD_ID = null;
                        SELECTED_CARD_DATA = null;
                        CURRENT_MATCH_STATE = data.match_state;
                        updateMatchView(CURRENT_MATCH_STATE);
                        runDynamicAiAnalysis(CURRENT_MATCH_STATE);
                        return;
                    }
                }
            } catch (err) {
                console.warn("[AUTO-PLACE] API call failed, falling back locally:", err);
            }
            await applyAiSetupRecommendation();
            await confirmInitialSetup();
        }

        function openSwitchModal() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING || CURRENT_MATCH_STATE.phase === 'SETUP') {
                alert("⚠️ You can only switch/retreat during your turn in the main battle phase!");
                return;
            }
            const bench = (CURRENT_MATCH_STATE.player.bench || []).filter(b => b !== null);
            if (bench.length === 0) {
                alert("⚠️ You have no Pokémon on your bench to switch with!");
                return;
            }
            const modal = document.getElementById('switch-modal');
            const list = document.getElementById('switch-bench-list');
            list.innerHTML = bench.map((b, idx) => `
                <div style="background:rgba(8,14,28,0.9); border:1px solid var(--neon-purple); border-radius:6px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:800; color:#fff;">#${idx+1}: ${b.name}</div>
                        <div style="font-size:0.7rem; color:var(--text-dim);">${b.current_hp}/${b.max_hp} HP • Energy: ${(b.attached_energy || []).length}</div>
                    </div>
                    <button class="btn-cyber-sm" style="border-color:var(--neon-purple); color:var(--neon-purple); padding:6px 12px;" onclick="executeRetreatSwitch(${idx})">
                        🔄 SWITCH IN
                    </button>
                </div>
            `).join('');
            modal.style.display = 'flex';
        }

        function closeSwitchModal() {
            const modal = document.getElementById('switch-modal');
            if (modal) modal.style.display = 'none';
        }

        async function executeRetreatSwitch(benchIndex) {
            closeSwitchModal();
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/retreat', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ bench_slot: benchIndex })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.result && data.result.status === 'error') {
                        alert(`⚠️ ${data.result.message}`);
                        return;
                    }
                    CURRENT_MATCH_STATE = data.match_state;
                    advanceWinningRouteStepIfType("SWITCH_POKEMON");
                    updateMatchView(CURRENT_MATCH_STATE);
                    runDynamicAiAnalysis(CURRENT_MATCH_STATE);
                    return;
                }
            } catch(e) {
                console.warn("Retreat switch API fallback:", e);
            }

            const bench = CURRENT_MATCH_STATE.player.bench || [];
            if (benchIndex < 0 || benchIndex >= bench.length) return;
            const oldActive = CURRENT_MATCH_STATE.player.active_spot;
            const newActive = bench.splice(benchIndex, 1)[0];
            CURRENT_MATCH_STATE.player.active_spot = newActive;
            bench.push(oldActive);
            CURRENT_MATCH_STATE.match_log.push(`🔄 Switched Active [${oldActive.name}] with Bench [${newActive.name}]! (Attached energy preserved).`);
            advanceWinningRouteStepIfType("SWITCH_POKEMON");
            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        function openKnockoutPromotionModal() {
            const bench = (CURRENT_MATCH_STATE.player.bench || []).filter(b => b !== null);
            if (bench.length === 0) {
                CURRENT_MATCH_STATE.winner = 'Opponent';
                CURRENT_MATCH_STATE.match_log.push("💀 Defeat: You have no benched Pokémon to promote! Opponent wins!");
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }
            const modal = document.getElementById('ko-modal');
            const list = document.getElementById('ko-bench-list');
            list.innerHTML = bench.map((b, idx) => `
                <div style="background:rgba(8,14,28,0.9); border:1px solid #ef4444; border-radius:6px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:800; color:#fff;">#${idx+1}: ${b.name}</div>
                        <div style="font-size:0.7rem; color:var(--text-dim);">${b.current_hp}/${b.max_hp} HP • Energy: ${(b.attached_energy || []).length}</div>
                    </div>
                    <button class="btn-action-main" style="border-color:var(--neon-green); padding:6px 12px; font-size:0.75rem;" onclick="executeKnockoutPromotion(${idx})">
                        👑 PROMOTE TO ACTIVE
                    </button>
                </div>
            `).join('');
            modal.style.display = 'flex';
        }

        async function executeKnockoutPromotion(benchIndex) {
            const modal = document.getElementById('ko-modal');
            if (modal) modal.style.display = 'none';

            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/promote-active', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ bench_slot: benchIndex })
                });
                if (res.ok) {
                    const data = await res.json();
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    return;
                }
            } catch(e) {
                console.warn("Promote active API fallback:", e);
            }

            const bench = CURRENT_MATCH_STATE.player.bench || [];
            if (benchIndex < 0 || benchIndex >= bench.length) return;
            const promoted = bench.splice(benchIndex, 1)[0];
            CURRENT_MATCH_STATE.player.active_spot = promoted;
            CURRENT_MATCH_STATE.match_log.push(`👑 Promoted [${promoted.name}] to Active Spot!`);
            updateMatchView(CURRENT_MATCH_STATE);
        }

        function updateMatchView(state) {
            if (!state) return;
            CURRENT_MATCH_STATE = state;
            window.CURRENT_MATCH_STATE = state;

            const pDeckCount = (state.player && (state.player.deck_count !== undefined ? state.player.deck_count : (state.player.deck || []).length)) || 0;
            const oppDeckCount = (state.opponent && (state.opponent.deck_count !== undefined ? state.opponent.deck_count : (state.opponent.deck || []).length)) || 0;

            const pKoEl = document.getElementById('p-ko-count');
            if (pKoEl) pKoEl.textContent = state.player.prizes_taken || 0;

            const oppKoEl = document.getElementById('opp-ko-count');
            if (oppKoEl) oppKoEl.textContent = state.opponent.prizes_taken || 0;

            const pDeckCountEl = document.getElementById('p-deck-count');
            if (pDeckCountEl) pDeckCountEl.textContent = pDeckCount;

            const pVisualDeckCount = document.getElementById('p-deck-count-visual');
            if (pVisualDeckCount) pVisualDeckCount.textContent = pDeckCount;

            const oppDeckCountEl = document.getElementById('opp-deck-count');
            if (oppDeckCountEl) oppDeckCountEl.textContent = oppDeckCount;
            const handLabel = document.getElementById('hand-count-label');
            if (handLabel) {
                if (state.phase === 'SETUP') {
                    const setupCards = (state.player.hand || []).filter(c => {
                        const m = getCardMeta(typeof c === 'string' ? c : (c.name || c.card_name));
                        return isBasicPokemon(m);
                    });
                    handLabel.textContent = setupCards.length;
                } else {
                    handLabel.textContent = (state.player.hand || []).length;
                }
            }

            const setupBanner = document.getElementById('match-setup-banner');
            if (setupBanner) {
                setupBanner.style.display = (state.phase === 'SETUP') ? 'block' : 'none';
            }

            const setupBottomBar = document.getElementById('setup-bottom-actions-bar');
            const matchActionBar = document.getElementById('match-actions-bar');
            if (state.phase === 'SETUP') {
                if (setupBottomBar) setupBottomBar.style.display = 'flex';
                if (matchActionBar) matchActionBar.style.display = 'none';
            } else {
                if (setupBottomBar) setupBottomBar.style.display = 'none';
                if (matchActionBar) matchActionBar.style.display = 'flex';
            }

            const drawBtn = document.getElementById('btn-claim-deck-card');
            if (drawBtn) {
                if (state.phase === 'SETUP') {
                    drawBtn.disabled = true;
                    drawBtn.style.opacity = '0.5';
                    drawBtn.style.cursor = 'not-allowed';
                    drawBtn.innerHTML = `🃏 DRAW LOCKED (SETUP PHASE)`;
                } else if (state.card_drawn_this_turn) {
                    drawBtn.disabled = true;
                    drawBtn.style.opacity = '0.5';
                    drawBtn.style.cursor = 'not-allowed';
                    drawBtn.innerHTML = `🃏 DECK CARD DRAWN (<span id="p-deck-count">${pDeckCount}</span> REMAINING)`;
                } else if (!state.is_player_turn || IS_AI_PROCESSING || state.winner) {
                    drawBtn.disabled = true;
                    drawBtn.style.opacity = '0.5';
                    drawBtn.style.cursor = 'not-allowed';
                    drawBtn.innerHTML = `🃏 DRAW DECK CARD (<span id="p-deck-count">${pDeckCount}</span> REMAINING)`;
                } else {
                    drawBtn.disabled = false;
                    drawBtn.style.opacity = '1';
                    drawBtn.style.cursor = 'pointer';
                    drawBtn.innerHTML = `🃏 DRAW DECK CARD (<span id="p-deck-count">${pDeckCount}</span> REMAINING)`;
                }
            }

            const energyBtn = document.getElementById('btn-add-energy-main');
            if (energyBtn) {
                if (state.phase === 'SETUP') {
                    energyBtn.disabled = true;
                    energyBtn.style.opacity = '0.5';
                    energyBtn.style.cursor = 'not-allowed';
                    energyBtn.innerHTML = `⚡ ENERGY LOCKED (SETUP PHASE)`;
                } else if (state.energy_attached_this_turn) {
                    energyBtn.disabled = true;
                    energyBtn.style.opacity = '0.5';
                    energyBtn.style.cursor = 'not-allowed';
                    energyBtn.innerHTML = `⚡ ENERGY ATTACHED (1/TURN USED)`;
                } else if (!state.is_player_turn || IS_AI_PROCESSING || state.winner) {
                    energyBtn.disabled = true;
                    energyBtn.style.opacity = '0.5';
                    energyBtn.style.cursor = 'not-allowed';
                    energyBtn.innerHTML = `⚡ + ATTACH ENERGY (1/TURN)`;
                } else {
                    energyBtn.disabled = false;
                    energyBtn.style.opacity = '1';
                    energyBtn.style.cursor = 'pointer';
                    energyBtn.innerHTML = `⚡ + ATTACH ENERGY (1/TURN)`;
                }
            }

            const switchBtn = document.getElementById('btn-switch-retreat');
            if (switchBtn) {
                if (state.phase === 'SETUP' || !state.is_player_turn || IS_AI_PROCESSING || state.winner) {
                    switchBtn.disabled = true;
                    switchBtn.style.opacity = '0.5';
                    switchBtn.style.cursor = 'not-allowed';
                } else {
                    switchBtn.disabled = false;
                    switchBtn.style.opacity = '1';
                    switchBtn.style.cursor = 'pointer';
                }
            }

            const endTurnBtn = document.getElementById('btn-end-turn');
            if (endTurnBtn) {
                if (state.phase === 'SETUP' || !state.is_player_turn || IS_AI_PROCESSING || state.winner) {
                    endTurnBtn.disabled = true;
                    endTurnBtn.style.opacity = '0.5';
                    endTurnBtn.style.cursor = 'not-allowed';
                } else {
                    endTurnBtn.disabled = false;
                    endTurnBtn.style.opacity = '1';
                    endTurnBtn.style.cursor = 'pointer';
                }
            }

            const pDeckBox = document.getElementById('player-face-down-deck');
            if (pDeckBox) {
                const canDraw = state.phase !== 'SETUP' && !state.card_drawn_this_turn && state.is_player_turn && !IS_AI_PROCESSING && !state.winner && (pDeckCount > 0);
                if (canDraw) {
                    pDeckBox.classList.remove('deck-disabled');
                    pDeckBox.style.pointerEvents = 'auto';
                    pDeckBox.style.cursor = 'pointer';
                } else {
                    pDeckBox.classList.add('deck-disabled');
                    pDeckBox.style.pointerEvents = 'none';
                    pDeckBox.style.cursor = 'not-allowed';
                }
            }

            // Render Opponent AI Hand (Face-Down Card Backs)
            const oppHandCount = (state.opponent.hand || []).length || state.opponent.hand_count || 5;
            const oppHandLabel = document.getElementById('opp-hand-count-label');
            if (oppHandLabel) oppHandLabel.textContent = oppHandCount;
            const oppHandView = document.getElementById('opp-hand-view');
            if (oppHandView) {
                let cardBacksHtml = '';
                for (let i = 0; i < oppHandCount; i++) {
                    cardBacksHtml += `
                        <div style="width:34px; height:48px; background:radial-gradient(circle at 50% 50%, #1e293b, #090e1a); border:1px solid rgba(255,0,127,0.4); border-radius:4px; display:inline-flex; align-items:center; justify-content:center; box-shadow:0 0 6px rgba(255,0,127,0.2);">
                            <div style="width:16px; height:16px; border-radius:50%; border:1px solid rgba(255,255,255,0.6); background:linear-gradient(180deg, #ef4444 50%, #fff 50%); display:flex; align-items:center; justify-content:center;">
                                <div style="width:5px; height:5px; background:#000; border-radius:50%;"></div>
                            </div>
                        </div>
                    `;
                }
                oppHandView.innerHTML = cardBacksHtml;
            }

            renderActiveCard('player-active-view', state.player.active_spot, true);
            renderActiveCard('opp-active-view', state.opponent.active_spot, false);
            renderBenchGrid('player-bench-view', state.player.bench, true);
            renderBenchGrid('opp-bench-view', state.opponent.bench, false);
            renderHandGrid(state.player.hand);
            renderCombatLog(state.match_log || []);

            const banner = document.getElementById('match-status-banner');
            if (banner) {
                if (state.phase === 'SETUP') {
                    banner.textContent = '🎯 SETUP PHASE (PLACE BASIC POKÉMON)';
                    banner.style.borderColor = 'var(--neon-amber)';
                    banner.style.color = 'var(--neon-amber)';
                } else if (state.winner) {
                    banner.textContent = state.winner === 'Player' ? '🏆 VICTORY: YOU WON!' : '❌ DEFEAT: OPPONENT WON';
                    banner.style.borderColor = state.winner === 'Player' ? 'var(--neon-green)' : '#ef4444';
                    banner.style.color = state.winner === 'Player' ? 'var(--neon-green)' : '#ef4444';
                } else {
                    banner.textContent = state.is_player_turn ? 'YOUR TURN' : 'OPPONENT AI TURN';
                    banner.style.borderColor = state.is_player_turn ? 'var(--neon-cyan)' : 'var(--neon-magenta)';
                    banner.style.color = state.is_player_turn ? 'var(--neon-cyan)' : 'var(--neon-magenta)';
                }
            }
        }

        function renderActiveCard(containerId, pkmn, isPlayer) {
            const box = document.getElementById(containerId);
            if (!box) return;
            if (!pkmn) {
                let placePrompt = '';
                if (isPlayer && SELECTED_CARD_DATA) {
                    const sName = typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name);
                    const sMeta = getCardMeta(sName);
                    if (isBasicPokemon(sMeta)) {
                        placePrompt = `
                            <button class="btn-action-main" style="margin-top:8px; border-color:var(--neon-green); color:#86efac; padding:6px 12px; font-size:0.75rem; font-weight:800;" onclick="playSelectedCard('active')">
                                👑 CLICK TO PLACE [${sName}] IN ACTIVE & START BATTLE
                            </button>
                        `;
                    }
                }
                box.innerHTML = `
                    <div style="padding:20px; text-align:center; color:var(--text-dim); border:2px dashed ${placePrompt ? 'var(--neon-cyan)' : 'rgba(255,255,255,0.15)'}; border-radius:8px; background:${placePrompt ? 'rgba(0,243,255,0.06)' : 'transparent'};">
                        <div style="font-size:1.8rem; margin-bottom:4px;">👑</div>
                        <div style="font-family:var(--font-orbitron); font-size:0.85rem; font-weight:800; color:${placePrompt ? 'var(--neon-cyan)' : 'var(--text-dim)'};">NO ACTIVE POKÉMON</div>
                        <div style="font-size:0.7rem; margin-top:2px;">Select a Basic Pokémon from hand to place here!</div>
                        ${placePrompt}
                    </div>
                `;
                return;
            }

            const meta = getCardMeta(pkmn.name);
            const maxHp = pkmn.max_hp || meta.hp || 100;
            const currHp = Math.max(0, pkmn.current_hp);
            const hpPct = Math.max(0, Math.min(100, (currHp / maxHp) * 100));
            const imgUrl = getCardImageUrl(meta, pkmn.name);
            const ptype = pkmn.pokemon_type || meta.pokemon_type || (meta.types && meta.types[0]) || 'Normal';

            // Opponent Active context for Type Advantage calculations
            const mState = CURRENT_MATCH_STATE || window.CURRENT_MATCH_STATE;
            const oppActive = isPlayer
                ? (mState && mState.opponent && mState.opponent.active_spot)
                : (mState && mState.player && mState.player.active_spot);
            const oppMeta = oppActive ? getCardMeta(oppActive.card_id || oppActive.name) : {};
            const oppType = oppActive ? (oppActive.pokemon_type || oppMeta.pokemon_type || (oppMeta.types && oppMeta.types[0]) || 'Colorless') : 'Colorless';
            const oppWeak = oppMeta.weakness || (oppActive && oppActive.weakness) || '';
            const oppRes = oppMeta.resistance || (oppActive && oppActive.resistance) || '';
            const myWeak = meta.weakness || pkmn.weakness || '';

            let attacksHtml = '';
            const attacks = (meta.attacks && meta.attacks.length > 0) ? meta.attacks : ((pkmn.attacks && pkmn.attacks.length > 0) ? pkmn.attacks : [{ name: "Strike", base_damage: 40, cost: ["Colorless"] }]);
            attacks.forEach(atk => {
                let strikeBtn = '';
                const isTurn = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.is_player_turn && !IS_AI_PROCESSING && !CURRENT_MATCH_STATE.winner && CURRENT_MATCH_STATE.phase !== 'SETUP';
                const costDetails = canPayAttackCostDetails(pkmn.attached_energy || pkmn.attachedEnergy || [], atk.cost || []);

                const baseDmg = atk.base_damage || 0;
                const matchup = calculateMatchupDamageJs(baseDmg, ptype, oppType, oppWeak, oppRes, myWeak);

                if (isPlayer) {
                    if (!isTurn) {
                        strikeBtn = `<button class="btn-cyber-sm" disabled style="opacity:0.4; cursor:not-allowed; padding:4px 8px; font-size:0.7rem;">⚡ STRIKE</button>`;
                    } else if (!costDetails.canAfford) {
                        strikeBtn = `<button class="btn-cyber-sm" disabled style="opacity:0.5; cursor:not-allowed; border-color:#ef4444; color:#f87171; padding:4px 8px; font-size:0.7rem; font-weight:700;" title="Requires: ${costDetails.costEmojis} • ${costDetails.reason}">⚡ NEED ENERGY</button>`;
                    } else {
                        strikeBtn = `<button class="btn-cyber-sm" onclick="matchAttack('${atk.name.replace(/'/g, "\\'")}', ${baseDmg || 30})" style="padding:4px 8px; font-size:0.7rem; border-color:var(--neon-green); color:#86efac; font-weight:800;" title="Ready to attack! ${matchup.desc}">⚡ STRIKE</button>`;
                    }
                }

                let costExplainer = '';
                if (isPlayer && !costDetails.canAfford) {
                    costExplainer = `<div style="font-size:0.65rem; color:#f87171; margin-top:2px; font-weight:600;">Requires: ${costDetails.costEmojis} • ${costDetails.reason}</div>`;
                }

                let dmgBadge = '';
                if (baseDmg > 0) {
                    if (matchup.mult === 1.5) {
                        dmgBadge = `<span style="color:#4ade80; font-size:0.8rem; font-weight:800;" title="${matchup.desc}">${matchup.finalDmg} DMG <small style="font-size:0.65rem; color:#86efac; font-weight:700;">(+50% Adv)</small></span>`;
                    } else if (matchup.mult === 0.5) {
                        dmgBadge = `<span style="color:#f87171; font-size:0.8rem; font-weight:800;" title="${matchup.desc}">${matchup.finalDmg} DMG <small style="font-size:0.65rem; color:#fca5a5; font-weight:700;">(-50% Disadv)</small></span>`;
                    } else {
                        dmgBadge = `<b style="color:var(--neon-amber); font-size:0.8rem;">${baseDmg} DMG</b>`;
                    }
                } else {
                    dmgBadge = `<b style="color:var(--text-dim); font-size:0.8rem;">Effect</b>`;
                }

                attacksHtml += `
                    <div style="background:rgba(255,255,255,0.04); padding:6px 8px; border-radius:4px; margin-top:4px; border:1px solid ${costDetails.canAfford ? 'rgba(0,255,136,0.2)' : 'rgba(239,68,68,0.2)'};">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="font-weight:800; font-size:0.78rem;">${atk.name}</div>
                                <div style="font-size:0.68rem; color:var(--text-dim);">Cost: ${costDetails.costEmojis} (${(atk.cost || ['Colorless']).join('/')})</div>
                                ${costExplainer}
                            </div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                ${dmgBadge}
                                ${strikeBtn}
                            </div>
                        </div>
                    </div>
                `;
            });

            // Target action button on active when card is selected
            let targetActionHtml = '';
            if (isPlayer && SELECTED_CARD_DATA && CURRENT_MATCH_STATE.phase !== 'SETUP') {
                const sName = typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name);
                const sMeta = getCardMeta(sName);
                if (sMeta.card_type === 'energy' || sName.toLowerCase().includes('energy')) {
                    if (!CURRENT_MATCH_STATE.energy_attached_this_turn) {
                        targetActionHtml = `
                            <button class="btn-cyber-sm" style="border-color:var(--neon-green); color:#86efac; padding:3px 8px; font-size:0.68rem; font-weight:800; margin-left:auto;" onclick="playSelectedCard('active')">
                                ⚡ ATTACH [${sName}]
                            </button>
                        `;
                    }
                } else if (sName.toLowerCase().includes('potion')) {
                    targetActionHtml = `
                        <button class="btn-cyber-sm" style="border-color:var(--neon-purple); color:#d8b4fe; padding:3px 8px; font-size:0.68rem; font-weight:800; margin-left:auto;" onclick="playSelectedCard('active')">
                            💊 HEAL (+30 HP)
                        </button>
                    `;
                } else if (sMeta.stage === 'Stage 1' || sMeta.stage === 'Stage 2') {
                    const evoFrom = (sMeta.evolves_from || '').toLowerCase().trim();
                    if (evoFrom && pkmn.name.toLowerCase().includes(evoFrom)) {
                        targetActionHtml = `
                            <button class="btn-cyber-sm" style="border-color:var(--neon-amber); color:#fde68a; padding:3px 8px; font-size:0.68rem; font-weight:800; margin-left:auto;" onclick="playSelectedCard('active')">
                                🔥 EVOLVE INTO [${sName}]
                            </button>
                        `;
                    }
                }
            }

            const attachedList = pkmn.attached_energy || pkmn.attachedEnergy || [];
            const energyDisplay = attachedList.length > 0
                ? attachedList.map(e => {
                    const etype = normalizeEnergyTypeJs(e);
                    const emoji = ENERGY_EMOJI_MAP[etype] || '⚡';
                    return `<span style="background:rgba(0,243,255,0.18); border:1px solid var(--neon-cyan); border-radius:4px; padding:2px 6px; font-size:0.72rem; margin-right:4px; font-weight:700; display:inline-flex; align-items:center; gap:3px;">${emoji} ${etype}</span>`;
                }).join('')
                : '<span style="color:var(--text-dim); font-size:0.7rem; font-style:italic;">None Attached</span>';

            const isEnergySelected = isPlayer && SELECTED_CARD_DATA && CURRENT_MATCH_STATE.phase !== 'SETUP' && (
                (getCardMeta(typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name)).card_type === 'energy') ||
                String(typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name)).toLowerCase().includes('energy')
            );
            if (isEnergySelected && !CURRENT_MATCH_STATE.energy_attached_this_turn) {
                box.style.border = '2px dashed var(--neon-green)';
                box.style.boxShadow = '0 0 16px rgba(0, 255, 136, 0.5), inset 0 0 10px rgba(0, 255, 136, 0.15)';
                box.style.cursor = 'pointer';
                box.setAttribute('onclick', "playSelectedCard('active')");
                box.setAttribute('title', '👉 Click to Attach selected Energy to Active Pokémon!');
            } else {
                box.style.border = '1px solid rgba(0, 243, 255, 0.3)';
                box.style.boxShadow = 'none';
                box.style.cursor = 'default';
                box.removeAttribute('onclick');
                box.removeAttribute('title');
            }

            box.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="font-family:var(--font-orbitron); font-size:0.92rem; color:${isPlayer ? 'var(--neon-cyan)' : 'var(--neon-magenta)'}; font-weight:900;">
                        ${isPlayer ? '👑 YOUR' : '👑 OPPONENT'} ACTIVE: ${pkmn.name}
                    </div>
                    <div style="display:flex; align-items:center; gap:6px;">
                        ${targetActionHtml}
                        <span class="cyber-badge" style="font-size:0.65rem; padding:2px 6px;">${ptype}</span>
                    </div>
                </div>

                <div style="display:flex; gap:12px; align-items:flex-start;">
                    <div class="active-card-img-box" style="width:85px; height:110px; min-width:85px; background:rgba(2,4,9,0.85); border:2px solid ${isPlayer ? 'var(--neon-cyan)' : 'var(--neon-magenta)'}; border-radius:8px; overflow:hidden; display:flex; align-items:center; justify-content:center; box-shadow:0 0 12px ${isPlayer ? 'rgba(0,243,255,0.25)' : 'rgba(255,0,85,0.25)'}; position:relative;">
                        <img src="${imgUrl}" alt="${pkmn.name}" style="max-width:100%; max-height:100%; object-fit:contain;"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                        <div style="display:none; font-size:2.2rem;">🐉</div>
                    </div>

                    <div style="flex:1;">
                        <div style="font-size:0.8rem; font-weight:800;">
                            HP: <span style="color:${currHp < 40 ? '#ef4444' : '#34d399'};">${currHp}</span> / ${maxHp}
                        </div>
                        <div style="height:6px; background:#111; border-radius:3px; margin:4px 0; overflow:hidden;">
                            <div style="width:${hpPct}%; background:${currHp < 40 ? '#ef4444' : (currHp < 80 ? '#f59e0b' : '#10b981')}; height:100%; transition:width 0.3s;"></div>
                        </div>
                        <div style="font-size:0.7rem; margin:4px 0;"><b>ENERGY:</b> ${energyDisplay}</div>
                        <div>${attacksHtml}</div>
                    </div>
                </div>
            `;
        }

        function renderBenchGrid(containerId, bench, isPlayer) {
            const box = document.getElementById(containerId);
            if (!box) return;
            const benchList = bench || [];

            let emptySlotsHtml = '';
            if (isPlayer && benchList.length < 3) {
                for (let slotIdx = benchList.length; slotIdx < 3; slotIdx++) {
                    let placeBtn = '';
                    if (SELECTED_CARD_DATA) {
                        const sName = typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name);
                        const sMeta = getCardMeta(sName);
                        if (isBasicPokemon(sMeta)) {
                            placeBtn = `<button class="btn-cyber-sm" style="border-color:var(--neon-green); color:#86efac; padding:2px 6px; font-size:0.65rem; font-weight:800; margin-left:auto;" onclick="playSelectedCard('bench_${slotIdx}')">🛡️ Place [${sName}] & Start Battle</button>`;
                        }
                    }
                    emptySlotsHtml += `
                        <div style="background:rgba(2,4,9,0.4); border:1px dashed rgba(255,255,255,0.15); border-radius:6px; padding:6px; font-size:0.7rem; display:flex; align-items:center; gap:8px;">
                            <div style="width:34px; height:42px; min-width:34px; background:rgba(0,0,0,0.3); border:1px dashed rgba(255,255,255,0.1); border-radius:4px; display:flex; align-items:center; justify-content:center; color:var(--text-dim); font-size:0.75rem;">
                                #${slotIdx+1}
                            </div>
                            <div style="color:var(--text-dim); font-size:0.68rem;">Empty Bench Slot</div>
                            ${placeBtn}
                        </div>
                    `;
                }
            }

            if (benchList.length === 0 && !emptySlotsHtml) {
                box.innerHTML = `<div style="color:var(--text-dim); font-size:0.7rem; font-style:italic;">Empty Bench (0/3 Slots)</div>`;
                return;
            }

            const itemsHtml = benchList.map((b, i) => {
                if (!b) return '';
                const maxHp = b.max_hp || 70;
                const currHp = Math.max(0, b.current_hp);
                const meta = getCardMeta(b.name);
                const thumbUrl = getCardImageUrl(meta, b.name);

                let benchActionBtn = '';
                if (isPlayer && SELECTED_CARD_DATA && CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.phase !== 'SETUP') {
                    const sName = typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name);
                    const sMeta = getCardMeta(sName);
                    if (sMeta.card_type === 'energy' || sName.toLowerCase().includes('energy')) {
                        if (!CURRENT_MATCH_STATE.energy_attached_this_turn) {
                            benchActionBtn = `<button class="btn-cyber-sm" style="border-color:var(--neon-green); color:#86efac; padding:2px 5px; font-size:0.62rem; font-weight:800;" onclick="playSelectedCard('bench_${i}')">⚡ Attach</button>`;
                        }
                    } else if (sName.toLowerCase().includes('potion')) {
                        benchActionBtn = `<button class="btn-cyber-sm" style="border-color:var(--neon-purple); color:#d8b4fe; padding:2px 5px; font-size:0.62rem; font-weight:800;" onclick="playSelectedCard('bench_${i}')">💊 Heal</button>`;
                    } else if (sMeta.stage === 'Stage 1' || sMeta.stage === 'Stage 2') {
                        const evoFrom = (sMeta.evolves_from || '').toLowerCase().trim();
                        if (evoFrom && b.name.toLowerCase().includes(evoFrom)) {
                            benchActionBtn = `<button class="btn-cyber-sm" style="border-color:var(--neon-amber); color:#fde68a; padding:2px 5px; font-size:0.62rem; font-weight:800;" onclick="playSelectedCard('bench_${i}')">🔥 Evolve</button>`;
                        }
                    }
                }

                return `
                    <div style="background:rgba(2,4,9,0.7); border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:6px; font-size:0.7rem; display:flex; align-items:center; gap:8px;">
                        <div style="width:34px; height:42px; min-width:34px; background:rgba(0,0,0,0.6); border:1px solid rgba(255,255,255,0.2); border-radius:4px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
                            <img src="${thumbUrl}" alt="${b.name}" style="max-width:100%; max-height:100%; object-fit:contain;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div style="display:none; font-size:1rem;">🛡️</div>
                        </div>
                        <div style="flex:1;">
                            <div style="display:flex; justify-content:space-between; font-weight:800;">
                                <span style="color:${isPlayer ? 'var(--neon-cyan)' : 'var(--neon-magenta)'};">#${i+1}: ${b.name}</span>
                                <span style="color:#34d399;">${currHp}/${maxHp} HP</span>
                            </div>
                            <div style="font-size:0.62rem; color:var(--text-dim); margin-top:2px; display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                                <span>Type: ${meta.pokemon_type || 'Basic'}</span>
                                <span>• Energy: ${(b.attached_energy || b.attachedEnergy || []).map(e => ENERGY_EMOJI_MAP[normalizeEnergyTypeJs(e)] || '⚡').join(' ') || 'None'}</span>
                            </div>
                        </div>
                        ${benchActionBtn}
                    </div>
                `;
            }).join('');

            box.innerHTML = itemsHtml + emptySlotsHtml;
        }

        function getAiSetupRecommendations(hand) {
            if (!hand || hand.length === 0) return null;
            if (LAST_AI_REPORT && LAST_AI_REPORT.setup_recommendation && LAST_AI_REPORT.setup_recommendation.recommended_main) {
                const recName = LAST_AI_REPORT.setup_recommendation.recommended_main.card_name;
                const inHand = hand.some(c => (typeof c === 'string' ? c : (c.name || c.card_name)) === recName);
                if (inHand) {
                    return LAST_AI_REPORT.setup_recommendation;
                }
            }

            const oppActive = (CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.active_spot) || {};
            const oppType = oppActive.pokemon_type || 'Colorless';
            const basicEvals = [];

            hand.forEach(c => {
                const cname = typeof c === 'string' ? c : (c.name || c.card_name);
                const meta = getCardMeta(cname);
                if (isBasicPokemon(meta)) {
                    const hp = meta.hp || 70;
                    const attacks = meta.attacks || [];
                    const maxDmg = attacks.reduce((max, a) => Math.max(max, a.base_damage || 0), 30);
                    const minCost = attacks.reduce((min, a) => Math.min(min, (a.cost || []).length || 1), 1);
                    const weakness = meta.weakness || '';
                    const hasDisadvantage = weakness.toLowerCase().includes(oppType.toLowerCase());

                    let winProb = 0.52 + (hp - 70) * 0.002 + (maxDmg - 30) * 0.003 - (minCost - 1) * 0.02;
                    if (hasDisadvantage) winProb -= 0.08;
                    winProb = Math.min(0.89, Math.max(0.45, winProb));

                    basicEvals.push({
                        card_name: cname,
                        hp: hp,
                        max_damage: maxDmg,
                        winning_probability: winProb,
                        winning_probability_pct: (winProb * 100).toFixed(1) + '%'
                    });
                }
            });

            basicEvals.sort((a, b) => b.winning_probability - a.winning_probability);
            if (basicEvals.length === 0) return null;

            const recMain = basicEvals[0];
            const recBench = basicEvals.slice(1, 4);
            return {
                recommended_main: recMain,
                recommended_bench: recBench,
                all_evaluations: basicEvals,
                summary: `Place [${recMain.card_name}] into Main (${recMain.winning_probability_pct} Win Possibility)` +
                         (recBench.length > 0 ? `, and [${recBench.map(b => b.card_name).join(', ')}] onto Bench.` : '.')
            };
        }

        function renderHandGrid(hand) {
            const box = document.getElementById('player-hand-view');
            if (!box) return;

            if (!hand || hand.length === 0) {
                box.innerHTML = '<div style="color:var(--text-dim); font-size:0.75rem;">Your hand is empty. Click [DRAW DECK CARD] to draw!</div>';
                return;
            }

            const isSetup = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.phase === 'SETUP';
            const isTurn = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.is_player_turn && !IS_AI_PROCESSING && !CURRENT_MATCH_STATE.winner;
            const energyAttached = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.energy_attached_this_turn;
            const pActive = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.active_spot;
            const pBench = (CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.bench) || [];
            const benchCount = pBench.filter(b => b !== null).length;

            const aiRec = getAiSetupRecommendations(hand);

            // Update Setup Banner AI Recommendation callout
            const setupBox = document.getElementById('setup-ai-rec-box');
            if (setupBox) {
                if (isSetup && aiRec && aiRec.summary) {
                    setupBox.style.display = 'block';
                    setupBox.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                            <div>
                                <span style="color:var(--neon-cyan); font-weight:900;">🧠 AI RECOMMENDATION:</span>
                                <span style="color:#fff; margin-left:6px;">${aiRec.summary}</span>
                            </div>
                            <button class="btn-action-main" style="background:rgba(0,243,255,0.2); border-color:var(--neon-cyan); color:#00f3ff; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="applyAiSetupRecommendation()">
                                ⚡ APPLY AI SETUP
                            </button>
                        </div>
                    `;
                } else {
                    setupBox.style.display = 'none';
                }
            }

            // Top Selected Card Action Bar
            let selectedActionBar = '';
            if (SELECTED_CARD_DATA) {
                const sName = typeof SELECTED_CARD_DATA === 'string' ? SELECTED_CARD_DATA : (SELECTED_CARD_DATA.name || SELECTED_CARD_DATA.card_name);
                const sMeta = getCardMeta(sName);
                const sBasic = isBasicPokemon(sMeta);
                const sEnergy = sMeta.card_type === 'energy' || sName.toLowerCase().includes('energy');
                const sTrainer = sMeta.card_type === 'trainer';
                const sEvo = sMeta.stage === 'Stage 1' || sMeta.stage === 'Stage 2';

                let actionBtns = '';
                if (isSetup) {
                    if (sBasic) {
                        actionBtns += `
                            <button class="btn-action-main" style="border-color:var(--neon-green); color:#86efac; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('active')">👑 Place Main & Start Battle</button>
                            <button class="btn-action-main" style="border-color:var(--neon-cyan); color:#38bdf8; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('bench')">🛡️ Place Bench & Start Battle</button>
                        `;
                    } else {
                        actionBtns += `<span style="color:#f87171; font-size:0.72rem;">Cannot place in setup.</span>`;
                    }
                } else {
                    if (sBasic) {
                        if (!pActive) {
                            actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-green); color:#86efac; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('active')">👑 Place Main</button>`;
                        }
                        if (benchCount < 3) {
                            actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-cyan); color:#38bdf8; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('bench')">🛡️ Place Bench</button>`;
                        }
                    } else if (sEnergy) {
                        actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-green); color:#86efac; padding:4px 10px; font-size:0.72rem; font-weight:800;" ${energyAttached ? 'disabled style="opacity:0.4;"' : ''} onclick="playSelectedCard('active')">⚡ Power Main</button>`;
                        pBench.forEach((b, bIdx) => {
                            if (b) {
                                actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-cyan); color:#38bdf8; padding:4px 10px; font-size:0.72rem; font-weight:800;" ${energyAttached ? 'disabled style="opacity:0.4;"' : ''} onclick="playSelectedCard('bench_${bIdx}')">⚡ Power Bench #${bIdx+1}</button>`;
                            }
                        });
                    } else if (sTrainer) {
                        const clean = sName.toLowerCase();
                        if (clean.includes('potion')) {
                            actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-purple); color:#d8b4fe; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('active')">💊 Heal Main</button>`;
                            pBench.forEach((b, bIdx) => {
                                if (b) {
                                    actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-purple); color:#d8b4fe; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('bench_${bIdx}')">💊 Heal Bench #${bIdx+1}</button>`;
                                }
                            });
                        } else {
                            actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-purple); color:#d8b4fe; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('active')">✨ Use Power</button>`;
                        }
                    } else if (sEvo) {
                        actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-amber); color:#fde68a; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('active')">🔥 Evolve Main</button>`;
                        pBench.forEach((b, bIdx) => {
                            if (b) {
                                actionBtns += `<button class="btn-action-main" style="border-color:var(--neon-amber); color:#fde68a; padding:4px 10px; font-size:0.72rem; font-weight:800;" onclick="playSelectedCard('bench_${bIdx}')">🔥 Evolve Bench #${bIdx+1}</button>`;
                            }
                        });
                    }
                }

                selectedActionBar = `
                    <div style="background:rgba(0, 243, 255, 0.08); border:1px solid var(--neon-cyan); border-radius:6px; padding:8px 12px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; box-shadow:0 0 12px rgba(0,243,255,0.2); width:100%;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="color:var(--neon-cyan); font-weight:900; font-size:0.78rem;">👉 SELECTED:</span>
                            <span style="color:#fff; font-weight:800; font-size:0.85rem;">${sName}</span>
                            <span style="font-size:0.7rem; color:var(--text-dim);">${sMeta.card_type || 'Card'} ${sMeta.stage ? '• ' + sMeta.stage : ''}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                            ${actionBtns}
                            <button class="btn-cyber-sm" style="border-color:#64748b; color:#94a3b8; padding:4px 8px; font-size:0.72rem;" onclick="selectHandCard(null, null, null, event)">✕ Cancel</button>
                        </div>
                    </div>
                `;
            }

            // During SETUP: Only cards that can be set in Main or Bench are in hand!
            const handCardsToRender = isSetup
                ? hand.filter(item => {
                    const cname = typeof item === 'string' ? item : (item.name || item.card_name);
                    return isBasicPokemon(getCardMeta(cname));
                })
                : hand;

            const cardsHtml = handCardsToRender.map((item, idx) => {
                const cname = typeof item === 'string' ? item : (item.name || item.card_name);
                const meta = getCardMeta(cname);
                const displayName = meta.name || meta.card_name || cname;
                const isBasic = isBasicPokemon(meta);
                const cardImg = getCardImageUrl(meta, cname);
                const isEnergy = meta.card_type === 'energy' || cname.toLowerCase().includes('energy');
                const isTrainer = meta.card_type === 'trainer';
                const isEvo = meta.stage === 'Stage 1' || meta.stage === 'Stage 2';

                const handKey = (item.card_id || cname) + '_' + idx;
                const isSelected = (SELECTED_CARD_KEY === handKey);

                // Check AI recommendation tags
                let aiBadge = '';
                let borderGlow = isSelected ? 'var(--neon-cyan)' : 'rgba(0,243,255,0.3)';
                if (aiRec && isBasic) {
                    if (aiRec.recommended_main && aiRec.recommended_main.card_name === cname) {
                        aiBadge = `<span style="background:rgba(0,243,255,0.25); border:1px solid var(--neon-cyan); border-radius:3px; padding:1px 5px; font-size:0.62rem; color:var(--neon-cyan); font-weight:900;">⭐ AI MAIN (${aiRec.recommended_main.winning_probability_pct})</span>`;
                        if (!isSelected) borderGlow = 'var(--neon-cyan)';
                    } else if (aiRec.recommended_bench && aiRec.recommended_bench.some(b => b.card_name === cname)) {
                        const bObj = aiRec.recommended_bench.find(b => b.card_name === cname);
                        aiBadge = `<span style="background:rgba(0,255,136,0.2); border:1px solid var(--neon-green); border-radius:3px; padding:1px 5px; font-size:0.62rem; color:#86efac; font-weight:800;">⭐ AI BENCH (${bObj ? bObj.winning_probability_pct : 'High'})</span>`;
                        if (!isSelected) borderGlow = 'var(--neon-green)';
                    }
                }

                const selectedBadge = isSelected ? `<span style="background:var(--neon-cyan); color:#000; font-weight:900; font-size:0.6rem; padding:1px 5px; border-radius:3px; margin-left:4px;">SELECTED</span>` : '';
                const selectedStyles = isSelected 
                    ? `border: 2px solid var(--neon-cyan); box-shadow: 0 0 15px rgba(0,243,255,0.7), inset 0 0 8px rgba(0,243,255,0.2); transform: translateY(-4px); background: rgba(0, 243, 255, 0.12);` 
                    : `border: 1px solid ${borderGlow}; box-shadow: ${borderGlow !== 'rgba(0,243,255,0.3)' ? '0 0 10px ' + borderGlow : 'none'}; background: rgba(8,14,28,0.95);`;

                if (isSetup) {
                    if (isBasic) {
                        return `
                            <div style="${selectedStyles} border-radius:6px; padding:6px 10px; display:inline-flex; align-items:center; gap:8px; font-size:0.75rem; cursor:pointer; transition:all 0.2s;" onclick="selectHandCard('${handKey}', '${cname.replace(/'/g, "\\'")}', ${idx}, event)">
                                <div style="width:28px; height:36px; min-width:28px; background:rgba(0,0,0,0.6); border:1px solid rgba(255,255,255,0.15); border-radius:3px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
                                    <img src="${cardImg}" alt="${displayName}" style="max-width:100%; max-height:100%; object-fit:contain;" onerror="this.style.display='none';">
                                </div>
                                <div>
                                    <div style="display:flex; align-items:center; gap:6px;">
                                        <span style="font-weight:800; color:#fff;">${displayName}</span>
                                        ${aiBadge}
                                        ${selectedBadge}
                                    </div>
                                    <div style="font-size:0.65rem; color:var(--neon-cyan);">${meta.hp || 70} HP • Basic Pokémon</div>
                                </div>
                                <div style="display:flex; gap:4px; margin-left:auto;">
                                    <button class="btn-cyber-sm" style="padding:4px 8px; font-size:0.7rem; border-color:var(--neon-green); color:#86efac; font-weight:800;" onclick="event.stopPropagation(); setupPlaceActive('${cname.replace(/'/g, "\\'")}')" title="Place as Main Active Pokémon and Start Battle!">👑 Main</button>
                                    <button class="btn-cyber-sm" style="padding:4px 8px; font-size:0.7rem; border-color:var(--neon-cyan); color:#38bdf8;" onclick="event.stopPropagation(); setupPlaceBench('${cname.replace(/'/g, "\\'")}')" title="Place on Bench and Start Battle!">🛡️ Bench</button>
                                </div>
                            </div>
                        `;
                    } else {
                        return '';
                    }
                }

                // Main BATTLE phase actions
                let actionButtons = '';
                if (isBasic) {
                    const benchBtn = `<button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem; border-color:var(--neon-cyan); color:#fff;" ${!isTurn || benchCount >= 3 ? 'disabled style="opacity:0.4;"' : ''} onclick="event.stopPropagation(); matchPlayCard('${cname.replace(/'/g, "\\'")}', 'bench')">🛡️ Bench</button>`;
                    const mainBtn = !pActive
                        ? `<button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem; border-color:var(--neon-green); color:#86efac;" ${!isTurn ? 'disabled style="opacity:0.4;"' : ''} onclick="event.stopPropagation(); matchPlayCard('${cname.replace(/'/g, "\\'")}', 'active')">👑 Main</button>`
                        : '';
                    actionButtons = mainBtn + benchBtn;
                } else if (isEvo) {
                    actionButtons = `
                        <button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem; border-color:var(--neon-amber); color:#fde68a;" ${!isTurn ? 'disabled style="opacity:0.4;"' : ''} onclick="event.stopPropagation(); matchPlayCard('${cname.replace(/'/g, "\\'")}', 'active')">🔥 Evolve Main</button>
                    `;
                } else if (isEnergy) {
                    actionButtons = `
                        <span class="btn-cyber-sm" style="padding:3px 6px; font-size:0.65rem; border-color:var(--neon-green); color:#86efac; font-weight:800;">⚡ Click to Attach</span>
                    `;
                } else if (isTrainer) {
                    const clean = cname.toLowerCase();
                    if (clean.includes('potion')) {
                        actionButtons = `
                            <button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem; border-color:var(--neon-purple); color:#d8b4fe;" ${!isTurn ? 'disabled style="opacity:0.4;"' : ''} onclick="event.stopPropagation(); matchPlayCard('${cname.replace(/'/g, "\\'")}', 'active')">💊 Heal Main</button>
                        `;
                    } else {
                        actionButtons = `
                            <button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem; border-color:var(--neon-purple); color:#d8b4fe;" ${!isTurn ? 'disabled style="opacity:0.4;"' : ''} onclick="event.stopPropagation(); matchPlayCard('${cname.replace(/'/g, "\\'")}')">✨ Use Power</button>
                        `;
                    }
                } else {
                    actionButtons = `
                        <button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem; border-color:var(--neon-purple); color:#d8b4fe;" ${!isTurn ? 'disabled style="opacity:0.4;"' : ''} onclick="event.stopPropagation(); matchPlayCard('${cname.replace(/'/g, "\\'")}')">Play</button>
                    `;
                }

                return `
                    <div style="${selectedStyles} border-radius:6px; padding:6px 8px; display:inline-flex; align-items:center; gap:8px; font-size:0.75rem; cursor:pointer; transition:all 0.2s;" onclick="selectHandCard('${handKey}', '${cname.replace(/'/g, "\\'")}', ${idx}, event)">
                        <div style="width:28px; height:36px; min-width:28px; background:rgba(0,0,0,0.6); border:1px solid rgba(255,255,255,0.15); border-radius:3px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
                            <img src="${cardImg}" alt="${displayName}" style="max-width:100%; max-height:100%; object-fit:contain;" onerror="this.style.display='none';">
                        </div>
                        <div>
                            <div style="display:flex; align-items:center; gap:4px;">
                                <span style="font-weight:800; color:#fff;">${displayName}</span>
                                ${aiBadge}
                                ${selectedBadge}
                            </div>
                            <div style="font-size:0.65rem; color:var(--neon-cyan);">${meta.hp ? meta.hp + ' HP' : (meta.card_type || 'Card')} ${meta.stage ? '• ' + meta.stage : ''}</div>
                        </div>
                        <div style="display:flex; gap:3px; flex-wrap:wrap; margin-left:auto;">
                            ${actionButtons}
                        </div>
                    </div>
                `;
            }).join('');

            if (isSetup && cardsHtml.trim() === '') {
                cardsHtml = '<div style="color:var(--neon-green); font-size:0.75rem; font-weight:700;">✅ All available Basic Pokémon have been placed. Click [CONFIRM INITIAL SETUP] or [START BATTLE] to begin!</div>';
            }

            box.innerHTML = selectedActionBar + cardsHtml;
        }

        function renderCombatLog(log) {
            const box = document.getElementById('combat-log');
            if (!box) return;
            box.innerHTML = (log || []).map(l => `<div>&gt; ${l}</div>`).join('');
            box.scrollTop = box.scrollHeight;
        }

        async function claimRandomDeckCard() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            if (CURRENT_MATCH_STATE.phase === 'SETUP') {
                alert("⚠️ Please finish initial setup before drawing cards!");
                return;
            }
            if (!CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) {
                alert("⏳ Please wait! It is the Opponent AI's turn.");
                return;
            }
            if (CURRENT_MATCH_STATE.card_drawn_this_turn) {
                alert("⚠️ You can only draw 1 deck card per turn!");
                return;
            }

            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/draw', { method: 'POST', headers: headers });
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'error') {
                        alert("⚠️ Draw blocked or deck is empty!");
                        return;
                    }
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    if (data.ai_recommendation) {
                        LAST_AI_REPORT = data.ai_recommendation;
                        renderStrategicAiReport(data.ai_recommendation);
                    }
                    return;
                }
            } catch(e) {
                console.warn("Draw API fallback:", e);
            }

            if (!CURRENT_MATCH_STATE.player.deck || CURRENT_MATCH_STATE.player.deck.length === 0) {
                alert("⚠️ Your deck is out of cards!");
                return;
            }
            const drawn = CURRENT_MATCH_STATE.player.deck.pop();
            CURRENT_MATCH_STATE.player.hand.push(drawn);
            CURRENT_MATCH_STATE.card_drawn_this_turn = true;
            CURRENT_MATCH_STATE.match_log.push(`🃏 Drew [${drawn}] from your 60-card deck.`);
            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        function getPokemonMaxEnergyLimit(pkmnName) {
            const meta = getCardMeta(pkmnName);
            let maxCost = 1;
            if (meta && meta.attacks && Array.isArray(meta.attacks)) {
                meta.attacks.forEach(a => {
                    const c = (a.cost || []).length || 1;
                    if (c > maxCost) maxCost = c;
                });
            }
            return Math.min(4, Math.max(2, maxCost + 1));
        }

        function advanceWinningRouteStepIfType(actionType) {
            if (LAST_AI_REPORT && LAST_AI_REPORT.winning_route && LAST_AI_REPORT.winning_route.steps) {
                const steps = LAST_AI_REPORT.winning_route.steps;
                if (CURRENT_ROUTE_STEP_INDEX < steps.length) {
                    const currentStep = steps[CURRENT_ROUTE_STEP_INDEX];
                    const stepType = (currentStep.action_type || currentStep.action || '').toUpperCase();
                    if (stepType.includes(actionType.toUpperCase()) || 
                       (actionType.startsWith('PLAY_') && stepType.startsWith('PLAY_'))) {
                        CURRENT_ROUTE_STEP_INDEX++;
                    }
                }
            }
        }

        async function promptAddEnergyDirect(target) {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            if (CURRENT_MATCH_STATE.phase === 'SETUP') {
                alert("⚠️ Please finish initial setup before attaching energy!");
                return;
            }
            if (!CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) {
                alert("⏳ Please wait! It is the Opponent AI's turn.");
                return;
            }
            if (CURRENT_MATCH_STATE.energy_attached_this_turn) {
                alert("⚡ Energy Rule: You can only attach 1 energy card from hand per turn!");
                return;
            }

            // Find an energy card in hand
            const hand = CURRENT_MATCH_STATE.player.hand || [];
            const energyCard = hand.find(c => {
                const m = getCardMeta(c);
                const cn = (m.name || (typeof c === 'string' ? c : c.name) || '').toLowerCase();
                return m.card_type === 'energy' || cn.includes('energy');
            });

            if (!energyCard) {
                alert("⚠️ You do not have an Energy card in your hand to attach!");
                return;
            }

            const cname = typeof energyCard === 'string' ? energyCard : (energyCard.name || energyCard.card_name || energyCard.card_id);
            let resolvedTarget = target;
            if (!resolvedTarget || resolvedTarget === 'player' || resolvedTarget === 'main') {
                resolvedTarget = 'active';
            }
            await matchPlayCard(cname, resolvedTarget);
        }

        async function matchPlayCard(cname, target = null) {
            if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) return;

            // Ensure cname is a string name/card_id, never an object
            if (cname && typeof cname === 'object') {
                cname = cname.name || cname.card_name || cname.card_id || String(cname);
            }
            if (!cname) return;

            if (CURRENT_MATCH_STATE.phase === 'SETUP') {
                const meta = getCardMeta(cname);
                if (!isBasicPokemon(meta)) {
                    alert("⚠️ Only Basic Pokémon can be placed during the Setup Phase!");
                    return;
                }
                if (target === 'bench' || (target && String(target).startsWith('bench'))) {
                    await setupPlaceBench(cname);
                } else if (target === 'active') {
                    await setupPlaceActive(cname);
                } else if (!CURRENT_MATCH_STATE.player.active_spot) {
                    await setupPlaceActive(cname);
                } else if ((CURRENT_MATCH_STATE.player.bench || []).length < 3) {
                    await setupPlaceBench(cname);
                } else {
                    alert("⚠️ Active spot and Bench (max 3) are already full!");
                }
                return;
            }

            console.log(`[PLAY CARD] Attempting to play [${cname}] with target: ${target}`);
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/play', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ card_name: cname, target: target || "active" })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'error' || (data.result && data.result.status === 'error')) {
                        const errMsg = (data.result && data.result.message) || data.message || "Invalid card play";
                        console.warn(`[ACTION REJECTED] ${errMsg}`);
                        alert(`⚠️ ${errMsg}`);
                        return;
                    }
                    CURRENT_MATCH_STATE = data.match_state;
                    console.log(`[PLAY CARD] Successfully played [${cname}]`);
                    updateMatchView(CURRENT_MATCH_STATE);
                    if (data.ai_recommendation) {
                        LAST_AI_REPORT = data.ai_recommendation;
                        renderStrategicAiReport(data.ai_recommendation);
                    }
                    return;
                }
            } catch(e) {
                console.warn("matchPlayCard API fallback:", e);
            }

            // Client-side fallback if backend unavailable
            const hand = CURRENT_MATCH_STATE.player.hand || [];
            const idx = hand.findIndex(c => (c.name || c) === cname || String(c.card_id || '') === String(cname));
            if (idx === -1) return;

            const clean = cname.toLowerCase().trim();
            const meta = getCardMeta(cname);
            const stype = (meta.card_type || meta.supertype || '').toLowerCase();
            const stage = meta.stage || '';
            const isEnergy = stype.includes('energy') || clean.includes('energy');
            const isTrainer = stype.includes('trainer') || stype.includes('item') || stype.includes('supporter');

            if (isTrainer) {
                hand.splice(idx, 1);
                CURRENT_MATCH_STATE.match_log.push(`📜 Played Trainer [${cname}].`);
                advanceWinningRouteStepIfType("PLAY_ITEM");
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }
            if (isEnergy) {
                if (CURRENT_MATCH_STATE.energy_attached_this_turn) {
                    alert("⚡ Energy Rule: You can only attach 1 energy card from hand per turn!");
                    return;
                }
                const pActive = CURRENT_MATCH_STATE.player.active_spot;
                if (!pActive) return;
                hand.splice(idx, 1);
                pActive.attached_energy.push(cname);
                CURRENT_MATCH_STATE.energy_attached_this_turn = true;
                CURRENT_MATCH_STATE.match_log.push(`⚡ Attached [${cname}] to active [${pActive.name}].`);
                advanceWinningRouteStepIfType("ATTACH_ENERGY");
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }
            if (stage === 'Stage 1' || stage === 'Stage 2' || meta.evolves_from) {
                const evoFrom = (meta.evolves_from || '').toLowerCase().trim();
                const pActive = CURRENT_MATCH_STATE.player.active_spot;
                if (pActive && evoFrom && pActive.name.toLowerCase().includes(evoFrom)) {
                    hand.splice(idx, 1);
                    const kept = pActive.attached_energy || [];
                    pActive.name = meta.name || cname;
                    pActive.max_hp = meta.hp || 120;
                    pActive.current_hp = pActive.max_hp;
                    pActive.attached_energy = kept;
                    pActive.image = meta.image || getCardImageUrl(meta, cname);
                    CURRENT_MATCH_STATE.match_log.push(`🔥 Evolved Active into [${pActive.name}]!`);
                    advanceWinningRouteStepIfType("EVOLVE_POKEMON");
                    updateMatchView(CURRENT_MATCH_STATE);
                    return;
                }
                alert(`⚠️ Cannot evolve: [${cname}] evolves from [${meta.evolves_from || 'Pre-evolution'}], which is not in play!`);
                return;
            }
            if (isBasicPokemon(meta)) {
                const bench = CURRENT_MATCH_STATE.player.bench || [];
                if (bench.length >= 3) {
                    alert("⚠️ Bench is full (maximum 3 Pokémon slots allowed)!");
                    return;
                }
                hand.splice(idx, 1);
                bench.push({ name: meta.name || cname, current_hp: meta.hp || 70, max_hp: meta.hp || 70, attached_energy: [], image: meta.image || getCardImageUrl(meta, cname) });
                CURRENT_MATCH_STATE.match_log.push(`🛡️ Placed Basic Pokémon [${cname}] onto Bench.`);
                advanceWinningRouteStepIfType("BENCH_POKEMON");
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }
        }

        async function matchAttack(atkName, dmg) {
            if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING || CURRENT_MATCH_STATE.phase === 'SETUP') return;

            console.log(`[ATTACK] Executing attack: ${atkName} (Base DMG: ${dmg})`);
            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/attack', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ attack_name: atkName, base_damage: dmg || 30 })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'error' || (data.result && data.result.status === 'error')) {
                        const errMsg = (data.result && data.result.message) || data.message || "Attack blocked";
                        console.warn(`[ACTION REJECTED] Attack blocked: ${errMsg}`);
                        alert(`⛔ ${errMsg}`);
                        return;
                    }
                    CURRENT_MATCH_STATE = data.match_state;
                    updateMatchView(CURRENT_MATCH_STATE);
                    if (data.ai_recommendation) {
                        LAST_AI_REPORT = data.ai_recommendation;
                        renderStrategicAiReport(data.ai_recommendation);
                    }
                    return;
                }
            } catch(e) {
                console.warn("matchAttack API fallback:", e);
            }

            const pActive = CURRENT_MATCH_STATE.player.active_spot;
            const oppActive = CURRENT_MATCH_STATE.opponent.active_spot;
            if (!pActive || !oppActive) return;

            const pMeta = getCardMeta(pActive.name);
            const oppMeta = getCardMeta(oppActive.name);
            const pType = pActive.pokemon_type || pMeta.pokemon_type || (pMeta.types && pMeta.types[0]) || 'Colorless';
            const oppType = oppActive.pokemon_type || oppMeta.pokemon_type || (oppMeta.types && oppMeta.types[0]) || 'Colorless';
            const matchup = calculateMatchupDamageJs(dmg, pType, oppType, oppMeta.weakness, oppMeta.resistance, pMeta.weakness);
            const finalDmg = matchup.finalDmg;

            oppActive.current_hp = Math.max(0, oppActive.current_hp - finalDmg);
            const matchupTag = matchup.mult === 1.5 ? ` (+50% Type Advantage vs ${oppType}!)` : (matchup.mult === 0.5 ? ` (-50% Type Disadvantage vs ${oppType})` : '');
            CURRENT_MATCH_STATE.match_log.push(`⚔️ Your [${pActive.name}] used [${atkName}] dealing ${finalDmg} DMG${matchupTag}!`);

            if (oppActive.current_hp <= 0) {
                CURRENT_MATCH_STATE.player.prizes_taken = (CURRENT_MATCH_STATE.player.prizes_taken || 0) + 1;
                CURRENT_MATCH_STATE.match_log.push(`🔥 Opponent's [${oppActive.name}] was KNOCKED OUT!`);
                if (CURRENT_MATCH_STATE.player.prizes_taken >= 3) {
                    CURRENT_MATCH_STATE.winner = 'Player';
                    updateMatchView(CURRENT_MATCH_STATE);
                    return;
                }
                const oppBench = CURRENT_MATCH_STATE.opponent.bench || [];
                if (oppBench.length > 0) {
                    const promoted = oppBench.shift();
                    CURRENT_MATCH_STATE.opponent.active_spot = {
                        name: promoted.name,
                        current_hp: promoted.max_hp || 100,
                        max_hp: promoted.max_hp || 100,
                        attached_energy: ["Basic Lightning Energy"]
                    };
                    CURRENT_MATCH_STATE.match_log.push(`🔄 Opponent promoted [${promoted.name}] to Active Spot!`);
                } else {
                    CURRENT_MATCH_STATE.winner = 'Player';
                    CURRENT_MATCH_STATE.match_log.push(`🏆 Opponent has no benched Pokémon to promote! You win!`);
                    updateMatchView(CURRENT_MATCH_STATE);
                    return;
                }
            }

            updateMatchView(CURRENT_MATCH_STATE);
            endPlayerTurn();
        }

        async function endPlayerTurn() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner || IS_AI_PROCESSING || CURRENT_MATCH_STATE.phase === 'SETUP') return;

            SELECTED_CARD_KEY = null;
            SELECTED_CARD_ID = null;
            SELECTED_CARD_DATA = null;
            IS_AI_PROCESSING = true;

            const turnBanner = document.getElementById('match-turn-banner');
            if (turnBanner) {
                turnBanner.style.background = 'rgba(239, 68, 68, 0.2)';
                turnBanner.style.borderColor = 'var(--neon-red)';
                turnBanner.textContent = '🤖 OPPONENT AI IS PLAYING...';
            }

            try {
                const headers = getMatchHeaders();
                const res = await fetch('/api/v1/match/pass-turn', { method: 'POST', headers: headers });
                if (res.ok) {
                    const data = await res.json();
                    await new Promise(r => setTimeout(r, 650));
                    CURRENT_MATCH_STATE = data.match_state;
                    IS_AI_PROCESSING = false;
                    updateMatchView(CURRENT_MATCH_STATE);
                    if (data.ai_recommendation) {
                        LAST_AI_REPORT = data.ai_recommendation;
                        renderStrategicAiReport(data.ai_recommendation);
                    }
                    return;
                }
            } catch(e) {
                console.warn("pass-turn API fallback:", e);
            }

            CURRENT_MATCH_STATE.is_player_turn = false;
            CURRENT_MATCH_STATE.match_log.push(`--- Opponent AI Turn ---`);
            updateMatchView(CURRENT_MATCH_STATE);
            executeAiTurn();
        }

        async function executeAiTurn() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            IS_AI_PROCESSING = true;

            const sleep = (ms) => new Promise(r => setTimeout(r, ms));
            await sleep(600);

            if (CURRENT_MATCH_STATE.opponent.deck && CURRENT_MATCH_STATE.opponent.deck.length > 0) {
                const drawn = CURRENT_MATCH_STATE.opponent.deck.pop();
                CURRENT_MATCH_STATE.opponent.hand.push(drawn);
                CURRENT_MATCH_STATE.match_log.push(`🤖 Opponent AI drew 1 card.`);
            }

            if (CURRENT_MATCH_STATE.opponent.active_spot) {
                CURRENT_MATCH_STATE.opponent.active_spot.attached_energy.push("Basic Lightning Energy");
                CURRENT_MATCH_STATE.match_log.push(`🤖 Opponent attached Energy to [${CURRENT_MATCH_STATE.opponent.active_spot.name}].`);
                updateMatchView(CURRENT_MATCH_STATE);
            }

            await sleep(600);

            const pActive = CURRENT_MATCH_STATE.player.active_spot;
            if (pActive && CURRENT_MATCH_STATE.opponent.active_spot) {
                const dmg = 40;
                pActive.current_hp = Math.max(0, pActive.current_hp - dmg);
                CURRENT_MATCH_STATE.match_log.push(`⚔️ Opponent's [${CURRENT_MATCH_STATE.opponent.active_spot.name}] attacked for ${dmg} DMG! (Your HP: ${pActive.current_hp}/${pActive.max_hp})`);

                if (pActive.current_hp <= 0) {
                    CURRENT_MATCH_STATE.opponent.prizes_taken = (CURRENT_MATCH_STATE.opponent.prizes_taken || 0) + 1;
                    CURRENT_MATCH_STATE.match_log.push(`🔥 Your [${pActive.name}] was KNOCKED OUT!`);

                    if (CURRENT_MATCH_STATE.opponent.prizes_taken >= 3) {
                        CURRENT_MATCH_STATE.winner = 'Opponent';
                        IS_AI_PROCESSING = false;
                        updateMatchView(CURRENT_MATCH_STATE);
                        return;
                    }

                    const pBench = CURRENT_MATCH_STATE.player.bench || [];
                    if (pBench.length > 0) {
                        openKnockoutPromotionModal();
                    } else {
                        CURRENT_MATCH_STATE.winner = 'Opponent';
                        CURRENT_MATCH_STATE.match_log.push("💀 You have no benched Pokémon to promote! Opponent wins!");
                        IS_AI_PROCESSING = false;
                        updateMatchView(CURRENT_MATCH_STATE);
                        return;
                    }
                }
            }

            CURRENT_MATCH_STATE.is_player_turn = true;
            CURRENT_MATCH_STATE.card_drawn_this_turn = false;
            CURRENT_MATCH_STATE.energy_attached_this_turn = false;
            CURRENT_ROUTE_STEP_INDEX = 0;
            CURRENT_MATCH_STATE.turn_number++;
            CURRENT_MATCH_STATE.match_log.push(`--- Turn ${CURRENT_MATCH_STATE.turn_number}: Your Turn ---`);

            if (CURRENT_MATCH_STATE.player.deck && CURRENT_MATCH_STATE.player.deck.length > 0) {
                const drawnCard = CURRENT_MATCH_STATE.player.deck.pop();
                CURRENT_MATCH_STATE.player.hand.push(drawnCard);
                CURRENT_MATCH_STATE.card_drawn_this_turn = true;
                CURRENT_MATCH_STATE.match_log.push(`🎴 Turn ${CURRENT_MATCH_STATE.turn_number} Start Draw: Took 1 card [${drawnCard}] from 60-card deck.`);
            }

            IS_AI_PROCESSING = false;
            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        let LAST_AI_REPORT = null;
        let CURRENT_ROUTE_STEP_INDEX = 0;

        function runDynamicAiAnalysis(state) {
            if (!state || state.winner) return;
            const pActive = state.player.active_spot;
            const oppActive = state.opponent.active_spot;
            const hpRatio = (pActive.current_hp / (oppActive.current_hp || 1));
            const winPct = Math.min(95, Math.max(10, Math.round(50 * hpRatio)));

            document.getElementById('left-win-pct').textContent = `${winPct}%`;
            document.getElementById('left-rec-action').textContent = `Strike with [${pActive.name}]`;
            document.getElementById('left-rec-desc').textContent = `Optimal sequence: Attach Energy, bench Basic Pokémon, then attack for maximum tempo advantage.`;
            document.getElementById('left-ranked-list').innerHTML = `
                <div>1. Attack active [${oppActive.name}] &bull; <span style="color:var(--neon-green); font-weight:800;">${winPct}% Win Rate</span></div>
                <div>2. Attach Energy to Bench Pokémon &bull; <span style="color:var(--neon-green); font-weight:800;">${Math.max(10, winPct - 8)}% Win Rate</span></div>
                <div>3. Draw additional cards &bull; <span style="color:var(--neon-green); font-weight:800;">${Math.max(10, winPct - 14)}% Win Rate</span></div>
            `;

            // Trigger POMDP MCTS Strategic Analysis in background
            fetchStrategicAiAnalysis('FAST');
        }

        async function fetchStrategicAiAnalysis(mode = 'FAST') {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            const btn = document.getElementById('btn-compute-winning-route');
            if (btn) {
                btn.innerHTML = '⏳ COMPUTING ROUTE...';
                btn.disabled = true;
            }

            try {
                const pAct = (CURRENT_MATCH_STATE.player && (CURRENT_MATCH_STATE.player.active_spot || CURRENT_MATCH_STATE.player.active_pokemon)) || { name: 'Active Pokémon', current_hp: 70, max_hp: 70, attached_energy: [] };
                const oppAct = (CURRENT_MATCH_STATE.opponent && (CURRENT_MATCH_STATE.opponent.active_spot || CURRENT_MATCH_STATE.opponent.active_pokemon)) || { name: 'Opponent Active', current_hp: 70, max_hp: 70, attached_energy: [] };
                const pDeckCount = (CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.deck_count !== undefined) ? CURRENT_MATCH_STATE.player.deck_count : ((CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.deck) || []).length;
                const oppDeckCount = (CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.deck_count !== undefined) ? CURRENT_MATCH_STATE.opponent.deck_count : ((CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.deck) || []).length;
                const oppHandCount = (CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.hand_count !== undefined) ? CURRENT_MATCH_STATE.opponent.hand_count : ((CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.hand) || []).length;

                const payload = {
                    game_state: {
                        turn_number: CURRENT_MATCH_STATE.turn_number || 1,
                        is_player_turn: CURRENT_MATCH_STATE.is_player_turn,
                        player: {
                            active_spot: {
                                name: pAct.name || 'Active',
                                current_hp: pAct.current_hp || 70,
                                max_hp: pAct.max_hp || 70,
                                attached_energy: pAct.attached_energy || []
                            },
                            active_pokemon: {
                                name: pAct.name || 'Active',
                                current_hp: pAct.current_hp || 70,
                                max_hp: pAct.max_hp || 70,
                                attached_energy: pAct.attached_energy || []
                            },
                            bench: ((CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.bench) || []).map(b => ({
                                name: b.name,
                                current_hp: b.current_hp,
                                max_hp: b.max_hp,
                                attached_energy: b.attached_energy || []
                            })),
                            hand: (CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.hand) || [],
                            deck_count: pDeckCount,
                            prizes_remaining: Math.max(1, 6 - ((CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.prizes_taken) || 0)),
                            prizes_taken: (CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.prizes_taken) || 0
                        },
                        opponent: {
                            active_spot: {
                                name: oppAct.name || 'Opponent Active',
                                current_hp: oppAct.current_hp || 70,
                                max_hp: oppAct.max_hp || 70,
                                attached_energy: oppAct.attached_energy || []
                            },
                            active_pokemon: {
                                name: oppAct.name || 'Opponent Active',
                                current_hp: oppAct.current_hp || 70,
                                max_hp: oppAct.max_hp || 70,
                                attached_energy: oppAct.attached_energy || []
                            },
                            bench: ((CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.bench) || []).map(b => ({
                                name: b.name,
                                current_hp: b.current_hp,
                                max_hp: b.max_hp,
                                attached_energy: b.attached_energy || []
                            })),
                            hand_count: oppHandCount,
                            deck_count: oppDeckCount,
                            prizes_remaining: Math.max(1, 6 - ((CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.prizes_taken) || 0)),
                            prizes_taken: (CURRENT_MATCH_STATE.opponent && CURRENT_MATCH_STATE.opponent.prizes_taken) || 0
                        }
                    },
                    mode: mode
                };

                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    const data = await res.json();
                    LAST_AI_REPORT = data;
                    CURRENT_ROUTE_STEP_INDEX = 0;
                    renderStrategicAiReport(data);
                }
            } catch (err) {
                console.warn("Notice: Online AI analysis fallback", err);
            } finally {
                if (btn) {
                    btn.innerHTML = '🧠 COMPUTE WINNING ROUTE';
                    btn.disabled = false;
                }
            }
        }

        function renderStrategicAiReport(data) {
            if (!data) return;

            const wr = data.winning_route;
            const steps = wr && wr.steps ? wr.steps : [];
            let activeStep = null;

            // Auto-advance past ATTACH_ENERGY if energy already attached this turn
            while (CURRENT_ROUTE_STEP_INDEX < steps.length && 
                   steps[CURRENT_ROUTE_STEP_INDEX].action_type === 'ATTACH_ENERGY' && 
                   CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.energy_attached_this_turn) {
                CURRENT_ROUTE_STEP_INDEX++;
            }

            if (steps.length > 0 && CURRENT_ROUTE_STEP_INDEX < steps.length) {
                activeStep = steps[CURRENT_ROUTE_STEP_INDEX];
            }

            // 1. Live Match Win Rate & Confidence Interval
            if (data.mathematical_analysis && data.mathematical_analysis.win_probability_after_pct) {
                document.getElementById('left-win-pct').textContent = data.mathematical_analysis.win_probability_after_pct;
            }
            const confElem = document.getElementById('left-confidence-interval');
            if (confElem && data.confidence) {
                confElem.textContent = `95% CI: ${data.confidence.confidence_interval_95} • ${data.operational_mode || 'MCTS'} (${data.confidence.simulations_conducted || 30} sims)`;
            }

            // 2. Best Move & Why (Dynamically reflects active step)
            if (activeStep) {
                document.getElementById('left-rec-action').textContent = `Step ${activeStep.step}: ${activeStep.action}`;
                document.getElementById('left-rec-desc').textContent = activeStep.strategic_impact || data.why || 'Execute recommended sequence to maintain route victory.';
            } else if (data.best_move) {
                document.getElementById('left-rec-action').textContent = data.best_move;
                if (data.why) {
                    document.getElementById('left-rec-desc').textContent = data.why;
                }
            }

            // 3. The Winning Route Roadmap with step states
            if (wr) {
                const turnsBadge = document.getElementById('left-route-turns');
                if (turnsBadge) {
                    turnsBadge.textContent = `${wr.estimated_turns_to_victory || 3} TURNS`;
                }
                const sumElem = document.getElementById('left-route-summary');
                if (sumElem) {
                    sumElem.textContent = wr.summary || `Winning Route to Victory (${wr.target_prizes_total || 6} Prizes)`;
                }
                const stepsElem = document.getElementById('left-route-steps');
                if (stepsElem && wr.steps) {
                    stepsElem.innerHTML = wr.steps.map((s, idx) => {
                        if (idx < CURRENT_ROUTE_STEP_INDEX) {
                            return `
                                <div style="background:rgba(0,255,136,0.08); border-left:3px solid var(--neon-green); padding:4px 8px; border-radius:3px; opacity:0.8;">
                                    <div style="font-weight:700; color:var(--neon-green);">Step ${s.step}: [COMPLETED ✅] <span style="text-decoration:line-through; color:var(--text-dim);">${s.action}</span></div>
                                    <div style="color:var(--text-dim); font-size:0.65rem;">Phase: ${s.phase} &bull; Action executed</div>
                                </div>
                            `;
                        } else if (idx === CURRENT_ROUTE_STEP_INDEX) {
                            return `
                                <div style="background:rgba(0,243,255,0.18); border-left:3px solid var(--neon-cyan); padding:5px 8px; border-radius:3px; box-shadow:0 0 10px rgba(0,243,255,0.25);">
                                    <div style="font-weight:800; color:#fff;">Step ${s.step}: [CURRENT STEP ⚡] <span style="color:var(--neon-cyan); font-weight:800;">${s.action}</span></div>
                                    <div style="color:var(--text-glow); font-size:0.65rem;">Phase: ${s.phase} &bull; Prizes: +${s.prizes_gained} (${s.remaining_needed} left)</div>
                                </div>
                            `;
                        } else {
                            return `
                                <div style="background:rgba(255,255,255,0.03); border-left:3px solid var(--text-dim); padding:4px 8px; border-radius:3px; opacity:0.7;">
                                    <div style="font-weight:600; color:var(--text-dim);">Step ${s.step}: [UPCOMING ⏳] <span style="color:#cbd5e1;">${s.action}</span></div>
                                    <div style="color:var(--text-dim); font-size:0.65rem;">Phase: ${s.phase} &bull; Prizes: +${s.prizes_gained} (${s.remaining_needed} left)</div>
                                </div>
                            `;
                        }
                    }).join('');
                }
                const condElem = document.getElementById('left-route-condition');
                if (condElem && wr.key_condition) {
                    condElem.textContent = `💡 Key: ${wr.key_condition}`;
                }
            }

            // 4. Top Ranked Plays with Deltas
            const rankedListElem = document.getElementById('left-ranked-list');
            if (rankedListElem) {
                let html = `<div>1. ${data.best_move} &bull; <span style="color:var(--neon-green); font-weight:800;">${data.mathematical_analysis ? data.mathematical_analysis.win_probability_after_pct : '--'}</span></div>`;
                if (data.alternative_moves && data.alternative_moves.length > 0) {
                    data.alternative_moves.slice(0, 3).forEach(alt => {
                        html += `<div>${alt.rank}. ${alt.action_name} &bull; <span style="color:#f87171; font-weight:700;">${alt.win_probability_pct} (${alt.delta_str})</span></div>`;
                    });
                }
                rankedListElem.innerHTML = html;
            }

            // 5. Predicted Opponent Counter & Response
            const oppDangElem = document.getElementById('left-opp-dangerous');
            const oppCountElem = document.getElementById('left-opp-counter');
            if (data.most_dangerous_response) {
                if (oppDangElem) {
                    oppDangElem.textContent = `${data.most_dangerous_response.description} (${data.most_dangerous_response.probability})`;
                }
                if (oppCountElem) {
                    oppCountElem.textContent = `Counter-strategy: ${data.most_dangerous_response.best_counter_move}`;
                }
            }

            // 6. Mathematical Formula & Expected Value
            const mathFormElem = document.getElementById('left-math-formula');
            const mathEvElem = document.getElementById('left-math-ev');
            if (data.mathematical_calculations) {
                if (mathFormElem) {
                    mathFormElem.textContent = data.mathematical_calculations.formula || 'Damage = Base * Type Multiplier (+50% Adv / -50% Disadv / Normal)';
                }
                if (mathEvElem) {
                    const ev = data.mathematical_calculations.expected_value_ev;
                    const ko = data.mathematical_calculations.knockout_probability_pct;
                    const risk = data.risk_assessment ? data.risk_assessment.risk_level : 'LOW';
                    mathEvElem.textContent = `EV: ${ev >= 0 ? '+' : ''}${ev} • KO Chance: ${ko} • Risk: ${risk}`;
                }
            }
        }

        async function executeAiRecommendation() {
            if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING || CURRENT_MATCH_STATE.winner) return;

            function getHandCardName(card) {
                if (!card) return null;
                if (typeof card === 'string') return card;
                return card.name || card.card_name || card.card_id || String(card);
            }

            // Sequential Winning Route Step Execution: Strictly 1 step per click!
            if (LAST_AI_REPORT && LAST_AI_REPORT.winning_route && LAST_AI_REPORT.winning_route.steps) {
                const steps = LAST_AI_REPORT.winning_route.steps;

                // Auto-advance if an energy attachment step is already satisfied
                while (CURRENT_ROUTE_STEP_INDEX < steps.length && 
                       steps[CURRENT_ROUTE_STEP_INDEX].action_type === 'ATTACH_ENERGY' && 
                       CURRENT_MATCH_STATE.energy_attached_this_turn) {
                    CURRENT_ROUTE_STEP_INDEX++;
                }

                if (CURRENT_ROUTE_STEP_INDEX < steps.length) {
                    const step = steps[CURRENT_ROUTE_STEP_INDEX];
                    const actType = (step.action_type || '').toUpperCase();
                    const pHand = CURRENT_MATCH_STATE.player.hand || [];

                    // 1. PLAY_ITEM / PLAY_SUPPORTER (One step)
                    if (actType === 'PLAY_ITEM' || actType === 'PLAY_SUPPORTER' || actType.startsWith('PLAY_')) {
                        const targetCard = step.card_name;
                        let cardToPlay = pHand.find(c => {
                            const cn = getHandCardName(c);
                            if (targetCard && cn && cn.toLowerCase() === targetCard.toLowerCase()) return true;
                            const meta = getCardMeta(c);
                            const stype = (meta.card_type || meta.supertype || '').toLowerCase();
                            return stype.includes('trainer') || stype.includes('item') || stype.includes('supporter') ||
                                   (cn && (cn.toLowerCase().includes('potion') || cn.toLowerCase().includes('research') || cn.toLowerCase().includes('ball') ||
                                           cn.toLowerCase().includes('switch') || cn.toLowerCase().includes('rope') || cn.toLowerCase().includes('boss')));
                        });

                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        if (cardToPlay) {
                            const cname = getHandCardName(cardToPlay);
                            await matchPlayCard(cname);
                        } else {
                            CURRENT_MATCH_STATE.match_log.push(`⚡ Executed hand power: ${step.action}.`);
                        }
                        if (CURRENT_ROUTE_STEP_INDEX === prevIdx) {
                            CURRENT_ROUTE_STEP_INDEX++;
                        }
                        updateMatchView(CURRENT_MATCH_STATE);
                        renderStrategicAiReport(LAST_AI_REPORT);
                        return; // Return immediately: only 1 step executed!
                    }

                    // 2. EVOLVE_POKEMON (One step)
                    if (actType === 'EVOLVE_POKEMON') {
                        const targetCard = step.card_name;
                        let cardToPlay = pHand.find(c => {
                            const cn = getHandCardName(c);
                            if (targetCard && cn && cn.toLowerCase() === targetCard.toLowerCase()) return true;
                            const meta = getCardMeta(c);
                            return (meta.stage === 'Stage 1' || meta.stage === 'Stage 2');
                        });

                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        if (cardToPlay) {
                            const cname = getHandCardName(cardToPlay);
                            await matchPlayCard(cname, 'active');
                        } else {
                            CURRENT_MATCH_STATE.match_log.push(`⚡ Executed hand power: ${step.action}.`);
                        }
                        if (CURRENT_ROUTE_STEP_INDEX === prevIdx) {
                            CURRENT_ROUTE_STEP_INDEX++;
                        }
                        updateMatchView(CURRENT_MATCH_STATE);
                        renderStrategicAiReport(LAST_AI_REPORT);
                        return; // Return immediately: only 1 step executed!
                    }

                    // 3. BENCH_POKEMON (One step)
                    if (actType === 'BENCH_POKEMON' || actType === 'PLAY_BASIC') {
                        const targetCard = step.card_name;
                        let cardToPlay = pHand.find(c => {
                            const cn = getHandCardName(c);
                            if (targetCard && cn && cn.toLowerCase() === targetCard.toLowerCase()) return true;
                            return isBasicPokemon(getCardMeta(c));
                        });

                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        if (cardToPlay) {
                            const cname = getHandCardName(cardToPlay);
                            await matchPlayCard(cname, 'bench');
                        } else {
                            CURRENT_MATCH_STATE.match_log.push(`⚡ Executed hand power: ${step.action}.`);
                        }
                        if (CURRENT_ROUTE_STEP_INDEX === prevIdx) {
                            CURRENT_ROUTE_STEP_INDEX++;
                        }
                        updateMatchView(CURRENT_MATCH_STATE);
                        renderStrategicAiReport(LAST_AI_REPORT);
                        return; // Return immediately: only 1 step executed!
                    }

                    // 4. ATTACH_ENERGY (One step)
                    if (actType === 'ATTACH_ENERGY') {
                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        const target = step.target_pokemon || 'active';
                        await promptAddEnergyDirect(target);
                        if (CURRENT_ROUTE_STEP_INDEX === prevIdx) {
                            CURRENT_ROUTE_STEP_INDEX++;
                        }
                        updateMatchView(CURRENT_MATCH_STATE);
                        renderStrategicAiReport(LAST_AI_REPORT);
                        return; // Return immediately: only 1 step executed!
                    }

                    // 5. ATTACK (Turn Finisher)
                    if (actType === 'ATTACK') {
                        CURRENT_ROUTE_STEP_INDEX++;
                        const atkName = step.attack_name || "Strike";
                        const dmg = step.damage || 40;
                        await matchAttack(atkName, dmg);
                        return; // Turn concludes
                    }
                }
            }

            // Fallback: Primary attack
            if (CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.active_spot) {
                const meta = getCardMeta(CURRENT_MATCH_STATE.player.active_spot.name);
                const atk = (meta.attacks && meta.attacks[0]) ? meta.attacks[0] : { name: "Strike", base_damage: 40 };
                await matchAttack(atk.name, atk.base_damage || 40);
            }
        }

        // ================= 7. PACK HISTORY =================
        async function loadPackHistory() {
            if (!AUTH_TOKEN) return;
            try {
                const res = await fetch('/api/v1/pack/history', {
                    headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
                });
                const data = await res.json();
                const list = document.getElementById('pack-history-list');
                if (!list) return;

                if (!data.history || data.history.length === 0) {
                    list.innerHTML = `<div style="color:var(--text-dim); padding:20px; text-align:center;">No pack opening history recorded yet. Open some packs!</div>`;
                    return;
                }

                list.innerHTML = data.history.map((h, idx) => `
                    <div style="background:rgba(2,4,9,0.75); border:1px solid rgba(0,243,255,0.25); border-radius:8px; padding:14px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                            <b style="color:var(--neon-cyan); font-family:var(--font-orbitron);">PACK #${data.history.length - idx}</b>
                            <span style="color:var(--text-dim); font-size:0.75rem; font-family:var(--font-mono);">${h.opened_at}</span>
                        </div>
                        <div style="display:flex; gap:8px; flex-wrap:wrap;">
                            ${h.cards.map(c => `
                                <div style="background:rgba(13,22,44,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:4px; padding:4px 8px; font-size:0.72rem;">
                                    <b>${c.name}</b> <span style="color:var(--neon-amber);">[${c.rarity}]</span> ${c.is_duplicate ? '<span style="color:#f59e0b;">(Dup)</span>' : '<span style="color:#00ff88;">(New)</span>'}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                console.error("Failed to load pack history:", err);
            }
        }

        // ================= 8. META PRESETS =================
        function renderDeckBuilderPreview(deckId) {
            const container = document.getElementById('deck-preview-cards');
            if (!container) return;

            let cards = [];
            if (deckId === 'miraidon-ex-regieleki') {
                cards = [
                    { name: "Miraidon ex", type: "Pokémon", count: 3 },
                    { name: "Iron Hands ex", type: "Pokémon", count: 2 },
                    { name: "Zapdos", type: "Pokémon", count: 2 },
                    { name: "Electric Generator", type: "Trainer", count: 4 },
                    { name: "Professor's Research", type: "Trainer", count: 4 },
                    { name: "Boss's Orders", type: "Trainer", count: 3 },
                    { name: "Basic Lightning Energy", type: "Energy", count: 18 }
                ];
            } else if (deckId === 'gardevoir-ex') {
                cards = [
                    { name: "Gardevoir ex", type: "Pokémon", count: 3 },
                    { name: "Ralts", type: "Pokémon", count: 4 },
                    { name: "Kirlia", type: "Pokémon", count: 4 },
                    { name: "Rare Candy", type: "Trainer", count: 4 },
                    { name: "Iono", type: "Trainer", count: 4 },
                    { name: "Basic Psychic Energy", type: "Energy", count: 16 }
                ];
            } else {
                cards = [
                    { name: "Charizard ex", type: "Pokémon", count: 3 },
                    { name: "Charmander", type: "Pokémon", count: 4 },
                    { name: "Charmeleon", type: "Pokémon", count: 2 },
                    { name: "Pidgeot ex", type: "Pokémon", count: 2 },
                    { name: "Rare Candy", type: "Trainer", count: 4 },
                    { name: "Arven", type: "Trainer", count: 4 },
                    { name: "Basic Fire Energy", type: "Energy", count: 16 }
                ];
            }

            container.innerHTML = cards.map(c => `
                <div style="background:rgba(13,22,44,0.85); border:1px solid rgba(0,243,255,0.2); border-radius:6px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <b style="color:#fff; font-size:0.85rem;">${c.name}</b>
                        <div style="font-size:0.68rem; color:var(--text-dim);">${c.type}</div>
                    </div>
                    <span class="cyber-badge" style="font-size:0.7rem; padding:2px 6px;">×${c.count}</span>
                </div>
            `).join('');
        }

        // --- INIT ON LOAD ---
        window.addEventListener('DOMContentLoaded', async () => {
            await loadAllCards();
            await checkAuthSession();
            await loadUserDecks();
            const activeDeck = USER_DECKS.find(d => d.is_active) || USER_DECKS[0];
            if (!activeDeck || !activeDeck.cards || activeDeck.cards.length === 0) {
                switchMode('cards');
                showDeckBuilderEmptyPrompt();
            } else {
                startNewMatch(false, true);
            }
        });
    </script>
</body>
</html>
"""
