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
            <!-- 4-CARD BATTLE SELECTION DOCK -->
            <div class="deck-builder-control-card" style="border: 2px solid var(--neon-cyan); box-shadow: 0 0 25px rgba(0,243,255,0.25); margin-bottom: 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-family:var(--font-orbitron); font-size:1.15rem; font-weight:900; color:var(--neon-cyan);">
                            🎯 CHOOSE YOUR 4 CARDS (BASIC POKÉMON ONLY)
                        </div>
                        <div style="font-size:0.82rem; color:var(--text-dim); margin-top:2px;">
                            Only Basic Pokémon can be chosen for starting slots. Pick 4 Basic Pokémon from your owned collection. Slot 1 becomes your Main Active Pokémon and Slots 2–4 become your Bench. Stage 1 & Stage 2 cards must be evolved legally during battle!
                        </div>
                    </div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <button id="btn-start-4cards" class="btn-action-main" style="padding:10px 20px; font-size:0.85rem; border-color:var(--neon-green); box-shadow:var(--neon-green-glow);" onclick="startBattleWithSelected4Cards()">
                            ⚔️ PLACE MY 4 CARDS & START BATTLE
                        </button>
                        <button class="btn-cyber-sm" style="background:var(--neon-amber); color:#000; font-weight:900; padding:10px 14px;" onclick="autoDealFromOwned()">
                            🎲 AUTO-DEAL FROM OWNED
                        </button>
                        <button class="btn-cyber-sm" style="border-color:#ef4444; color:#fca5a5; padding:10px 14px;" onclick="resetChosen4Cards()">
                            🔄 RESET
                        </button>
                    </div>
                </div>

                <!-- 4 Slots Display -->
                <div class="slots-row">
                    <div id="slot-card-1" class="cd-stat-pill" style="border:2px solid var(--neon-cyan); background:rgba(0,243,255,0.12); flex-direction:column; align-items:flex-start; padding:10px; border-radius:8px;">
                        <div style="font-size:0.7rem; color:var(--neon-cyan); font-family:var(--font-orbitron); font-weight:800;">👑 SLOT 1: MAIN ACTIVE (BASIC ONLY)</div>
                        <div id="slot-name-1" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Select Basic Pokémon</div>
                        <div id="slot-type-1" style="font-size:0.7rem; color:#cbd5e1;">Empty Slot</div>
                    </div>
                    <div id="slot-card-2" class="cd-stat-pill" style="border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.06); flex-direction:column; align-items:flex-start; padding:10px; border-radius:8px;">
                        <div style="font-size:0.7rem; color:var(--neon-green); font-family:var(--font-orbitron); font-weight:800;">🛡️ SLOT 2: BENCH SUB #1 (BASIC ONLY)</div>
                        <div id="slot-name-2" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Select Basic Pokémon</div>
                        <div id="slot-type-2" style="font-size:0.7rem; color:#cbd5e1;">Empty Slot</div>
                    </div>
                    <div id="slot-card-3" class="cd-stat-pill" style="border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.06); flex-direction:column; align-items:flex-start; padding:10px; border-radius:8px;">
                        <div style="font-size:0.7rem; color:var(--neon-green); font-family:var(--font-orbitron); font-weight:800;">🛡️ SLOT 3: BENCH SUB #2 (BASIC ONLY)</div>
                        <div id="slot-name-3" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Select Basic Pokémon</div>
                        <div id="slot-type-3" style="font-size:0.7rem; color:#cbd5e1;">Empty Slot</div>
                    </div>
                    <div id="slot-card-4" class="cd-stat-pill" style="border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.06); flex-direction:column; align-items:flex-start; padding:10px; border-radius:8px;">
                        <div style="font-size:0.7rem; color:var(--neon-green); font-family:var(--font-orbitron); font-weight:800;">🛡️ SLOT 4: BENCH SUB #3 (BASIC ONLY)</div>
                        <div id="slot-name-4" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Select Basic Pokémon</div>
                        <div id="slot-type-4" style="font-size:0.7rem; color:#cbd5e1;">Empty Slot</div>
                    </div>
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
                        <div id="left-math-formula" style="color:var(--neon-cyan); word-break:break-all;">Damage = (Base + Bonus) * Weakness - Resist</div>
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
                    <!-- OPPONENT TOP BOARD: SUB POKÉMON & DECK -->
                    <div>
                        <div class="section-label" style="color:var(--neon-magenta);"><span>OPPONENT SUB POKÉMON (3 SLOTS)</span></div>
                        <div id="opp-bench-view" class="bench-grid"></div>
                    </div>

                    <!-- OPPONENT MAIN POKÉMON -->
                    <div class="active-spot-center">
                        <div class="section-label" style="color:var(--neon-magenta);"><span>👑 OPPONENT MAIN POKÉMON</span></div>
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
                        <div class="section-label" style="color:var(--neon-cyan);"><span>👑 YOUR MAIN POKÉMON</span></div>
                        <div id="player-active-view" class="visual-active-card"></div>
                    </div>

                    <!-- PLAYER BOTTOM BOARD: SUB POKÉMON -->
                    <div>
                        <div class="section-label" style="color:var(--neon-cyan);"><span>YOUR SUB POKÉMON (3 SLOTS)</span></div>
                        <div id="player-bench-view" class="bench-grid"></div>
                    </div>

                    <!-- PLAYER HAND CARDS -->
                    <div>
                        <div class="section-label"><span>YOUR HAND CARDS (DRAWN FROM COLLECTION DECK)</span></div>
                        <div id="player-hand-view" class="hand-grid"></div>
                    </div>

                    <!-- MATCH CONTROLS -->
                    <div class="match-actions-bar">
                        <button id="btn-claim-deck-card" class="btn-action-main" style="border-color:var(--neon-cyan); padding:8px 14px; font-size:0.75rem;" onclick="claimRandomDeckCard()">
                            🃏 DRAW DECK CARD (<span id="p-deck-count">34</span> REMAINING)
                        </button>
                        <button id="btn-add-energy-main" class="btn-action-main" style="border-color:var(--neon-amber); padding:8px 14px; font-size:0.75rem;" onclick="promptAddEnergyDirect('player')">
                            ⚡ + ATTACH ENERGY (1/TURN)
                        </button>
                        <button class="btn-action-main" style="border-color:var(--neon-green); padding:8px 14px; font-size:0.75rem;" onclick="endPlayerTurn()">
                            ⏭️ END TURN & LET OPPONENT PLAY
                        </button>
                    </div>
                </div>

                <!-- RIGHT COLUMN: SCOREBOARD & LOGS -->
                <div class="side-column-panel">
                    <div class="section-label"><span>📊 SCOREBOARD & LOGS</span></div>
                    <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(0,243,255,0.2); border-radius:8px; padding:10px;">
                        <div style="display:flex; justify-content:space-between; font-family:var(--font-orbitron); font-size:0.85rem;">
                            <span style="color:var(--neon-green);">YOUR KOs: <b id="p-ko-count" style="font-size:1.1rem;">0</b>/3</span>
                            <span style="color:var(--neon-magenta);">OPP KOs: <b id="opp-ko-count" style="font-size:1.1rem;">0</b>/3</span>
                        </div>
                        <div id="match-status-banner" class="cyber-badge" style="margin-top:8px; width:100%; justify-content:center;">MATCH IN PROGRESS</div>
                    </div>

                    <div>
                        <button class="btn-action-main" style="width:100%; padding:8px; font-size:0.75rem; margin-bottom:8px;" onclick="switchMode('cards')">
                            🎴 SELECT CARDS FROM COLLECTION
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

        let CHOSEN_4_CARDS = getRandomBasicPokemon(4);
        let OPPONENT_4_CARDS = getRandomBasicPokemon(4, CHOSEN_4_CARDS);
        let CURRENT_MATCH_STATE = null;
        let CURRENT_PACK_REVEAL = [];
        let FILTER_CATEGORY = 'all';
        let FILTER_STAGE = 'all';
        let FILTER_RARITY = 'all';
        let SEARCH_QUERY = '';
        let IS_AI_PROCESSING = false;
        let filterDebounceTimer = null;

        function canPayAttackCost(attachedEnergies, costList) {
            if (!costList || costList.length === 0) return true;
            return (attachedEnergies || []).length >= costList.length;
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
                        ${isBasic ? `<button class="btn-cyber-sm btn-choose-4" style="flex:1; padding:6px 8px; font-size:0.7rem; text-align:center;">🎯 SELECT FOR 4-CARD BATTLE</button>` : ''}
                    </div>
                `;

                const btn4 = div.querySelector('.btn-choose-4');
                if (btn4) btn4.onclick = () => chooseCardFor4Slot(card.name);

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

        // ================= 5. 4-CARD SELECTION & BATTLE ENGINE =================
        function updateChosen4CardsUI() {
            for (let i = 0; i < 4; i++) {
                const cname = CHOSEN_4_CARDS[i];
                const nameEl = document.getElementById(`slot-name-${i+1}`);
                const typeEl = document.getElementById(`slot-type-${i+1}`);
                if (!cname) {
                    if (nameEl) nameEl.textContent = 'Empty Slot';
                    if (typeEl) typeEl.textContent = 'Select Basic Pokémon';
                } else {
                    const meta = getCardMeta(cname);
                    if (nameEl) nameEl.textContent = `${cname} (${meta.hp || 70} HP)`;
                    if (typeEl) typeEl.textContent = `Type: ${meta.pokemon_type || 'Normal'} • Top Atk: ${(meta.attacks && meta.attacks[0]) ? meta.attacks[0].base_damage + ' DMG' : 'Support'}`;
                }
            }
        }

        function chooseCardFor4Slot(cname) {
            const meta = getCardMeta(cname);
            if (!isBasicPokemon(meta)) {
                alert(`❌ Invalid Selection: Only Basic Pokémon can be chosen for starting slots!\\n\\n'${cname}' is a ${meta.stage || 'Stage 1/2'} Pokémon and must be evolved during gameplay.`);
                return;
            }

            if (!meta || !meta.quantity || meta.quantity <= 0) {
                alert(`⚠️ You do not own '${cname}'! Open booster packs to collect it.`);
                return;
            }

            let idx = CHOSEN_4_CARDS.indexOf(cname);
            if (idx !== -1) {
                alert(`ℹ️ '${cname}' is already selected in Slot #${idx+1}.`);
                return;
            }

            if (CHOSEN_4_CARDS.length >= 4) {
                CHOSEN_4_CARDS.shift();
            }
            CHOSEN_4_CARDS.push(cname);
            updateChosen4CardsUI();
        }

        function resetChosen4Cards() {
            CHOSEN_4_CARDS = [];
            updateChosen4CardsUI();
        }

        function autoDealFromOwned(silent = false) {
            const basicOwned = OWNED_CARDS.filter(c => isBasicPokemon(c));
            const chosen = [];
            const shuffled = [...basicOwned].sort(() => 0.5 - Math.random());
            for (let c of shuffled) {
                if (chosen.length >= 4) break;
                if (!chosen.includes(c.name)) chosen.push(c.name);
            }
            if (chosen.length < 4) {
                const fallback = getRandomBasicPokemon(4, chosen);
                for (let name of fallback) {
                    if (chosen.length >= 4) break;
                    chosen.push(name);
                }
            }
            CHOSEN_4_CARDS = chosen;
            updateChosen4CardsUI();
        }

        function getCardMeta(cname) {
            if (!cname) return { name: "Unknown", card_type: "pokemon", stage: "Basic", hp: 70, pokemon_type: "Normal", attacks: [] };
            const clean = cname.toLowerCase().trim();
            if (OWNED_CARDS_MAP[clean]) return OWNED_CARDS_MAP[clean];
            if (clean.includes('energy')) {
                return { name: cname, card_type: "energy", supertype: "Energy", stage: "" };
            }
            if (clean.includes('potion') || clean.includes('research') || clean.includes('ball') || clean.includes('switch') || clean.includes('boss') || clean.includes('trainer') || clean.includes('supporter') || clean.includes('item') || clean.includes('rope')) {
                return { name: cname, card_type: "trainer", supertype: "Trainer", stage: "" };
            }
            const isEx = clean.includes('ex');
            return {
                name: cname,
                card_type: "pokemon",
                stage: "Basic",
                subtypes: ["Basic"],
                hp: isEx ? 220 : 70,
                pokemon_type: "Normal",
                attacks: [{ name: "Strike", base_damage: 40 }]
            };
        }

        async function startBattleWithSelected4Cards() {
            if (CHOSEN_4_CARDS.length < 4) {
                alert("⚠️ Please pick 4 Basic Pokémon for your battle slots first!");
                return;
            }

            for (const cname of CHOSEN_4_CARDS) {
                const meta = getCardMeta(cname);
                if (!isBasicPokemon(meta)) {
                    alert(`❌ Cannot start battle: '${cname}' is not a Basic Pokémon! Only Basic Pokémon can be chosen for starting slots.`);
                    return;
                }
            }

            startNewMatch(true);
            switchMode('match');
        }

        // ================= 6. MATCH ARENA SIMULATION =================
        function buildOwned60CardDeck(chosenBasics) {
            const deck = [];
            chosenBasics.forEach(n => {
                for (let i = 0; i < 3; i++) deck.push(n);
            });

            const ownedEvos = OWNED_CARDS.filter(c => c.card_type === 'pokemon' && (c.stage === 'Stage 1' || c.stage === 'Stage 2'));
            for (const evo of ownedEvos) {
                if (deck.length >= 28) break;
                const addCount = Math.min(2, evo.quantity || 1);
                for (let i = 0; i < addCount; i++) {
                    if (deck.length < 28) deck.push(evo.name);
                }
            }

            const ownedTrainers = OWNED_CARDS.filter(c => c.card_type === 'trainer');
            for (const tr of ownedTrainers) {
                if (deck.length >= 44) break;
                const addCount = Math.min(2, tr.quantity || 1);
                for (let i = 0; i < addCount; i++) {
                    if (deck.length < 44) deck.push(tr.name);
                }
            }

            const fallbackTrainers = ["Potion", "Poké Ball", "Switch", "Professor's Research", "Ultra Ball"];
            for (const ft of fallbackTrainers) {
                if (deck.length < 44) deck.push(ft);
            }

            const energyTypes = ["Basic Fire Energy", "Basic Lightning Energy", "Basic Water Energy", "Basic Psychic Energy", "Basic Fighting Energy", "Basic Grass Energy"];
            let eIdx = 0;
            while (deck.length < 60) {
                deck.push(energyTypes[eIdx % energyTypes.length]);
                eIdx++;
            }

            return fisherYatesShuffle(deck);
        }

        function buildOpponent60CardDeck() {
            const oppBasics = ["Miraidon ex", "Zapdos", "Pikachu", "Iron Hands ex"];
            const deck = [];
            oppBasics.forEach(n => {
                for (let i = 0; i < 3; i++) deck.push(n);
            });
            const oppEvos = ["Raichu", "Tyranitar ex", "Magcargo ex"];
            oppEvos.forEach(n => {
                for (let i = 0; i < 2; i++) deck.push(n);
            });
            const oppTrainers = ["Professor's Research", "Boss's Orders", "Switch", "Ultra Ball", "Electric Generator"];
            oppTrainers.forEach(n => {
                for (let i = 0; i < 3; i++) deck.push(n);
            });
            while (deck.length < 60) {
                deck.push("Basic Lightning Energy");
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

        function startNewMatch(keepPlayerCards = false) {
            if (!keepPlayerCards || CHOSEN_4_CARDS.length < 4) {
                autoDealFromOwned(true);
            }

            const pBasics = CHOSEN_4_CARDS.length >= 4 ? CHOSEN_4_CARDS : ["Charmander", "Pikachu", "Eevee", "Snorlax"];
            const pDeck = buildOwned60CardDeck(pBasics);
            const oppDeck = buildOpponent60CardDeck();

            const pActiveName = pBasics[0];
            const pActiveMeta = getCardMeta(pActiveName);

            const oppBasics = (typeof OPPONENT_4_CARDS !== 'undefined' && OPPONENT_4_CARDS && OPPONENT_4_CARDS.length >= 4)
                ? OPPONENT_4_CARDS
                : ["Miraidon ex", "Pikachu", "Zapdos", "Iron Hands ex"];
            const oppActiveName = oppBasics[0];
            const oppActiveMeta = getCardMeta(oppActiveName);
            const oppBench1Meta = getCardMeta(oppBasics[1]);
            const oppBench2Meta = getCardMeta(oppBasics[2]);
            const oppBench3Meta = getCardMeta(oppBasics[3]);

            CURRENT_ROUTE_STEP_INDEX = 0;
            CURRENT_MATCH_STATE = {
                turn_number: 1,
                is_player_turn: true,
                card_drawn_this_turn: false,
                energy_attached_this_turn: false,
                winner: null,
                player: {

                    name: CURRENT_USER ? CURRENT_USER.username : "Player",
                    active_spot: {
                        name: pActiveName,
                        current_hp: pActiveMeta.hp || 70,
                        max_hp: pActiveMeta.hp || 70,
                        attached_energy: [],
                        card_id: pActiveMeta.card_id
                    },
                    bench: [
                        { name: pBasics[1], current_hp: 60, max_hp: 60, attached_energy: [] },
                        { name: pBasics[2], current_hp: 60, max_hp: 60, attached_energy: [] },
                        { name: pBasics[3], current_hp: 70, max_hp: 70, attached_energy: [] }
                    ],
                    hand: [pDeck.pop(), pDeck.pop(), pDeck.pop(), pDeck.pop()],
                    deck: pDeck,
                    discard: [],
                    prizes_taken: 0
                },
                opponent: {
                    name: "Opponent AI",
                    active_spot: {
                        name: oppActiveName,
                        current_hp: oppActiveMeta.hp || 220,
                        max_hp: oppActiveMeta.hp || 220,
                        attached_energy: ["Basic Lightning Energy"]
                    },
                    bench: [
                        { name: oppBasics[1], current_hp: oppBench1Meta.hp || 60, max_hp: oppBench1Meta.hp || 60, attached_energy: [] },
                        { name: oppBasics[2], current_hp: oppBench2Meta.hp || 60, max_hp: oppBench2Meta.hp || 60, attached_energy: [] },
                        { name: oppBasics[3], current_hp: oppBench3Meta.hp || 70, max_hp: oppBench3Meta.hp || 70, attached_energy: [] }
                    ],
                    hand: [oppDeck.pop(), oppDeck.pop(), oppDeck.pop(), oppDeck.pop()],
                    deck: oppDeck,
                    discard: [],
                    prizes_taken: 0
                },
                match_log: [
                    "⚔️ Match initialized with cards from your personal collection!",
                    `👑 Active Pokémon: [${pActiveName}] vs [${oppActiveName}].`,
                    "Turn 1: It is your turn!"
                ]
            };

            updateMatchView(CURRENT_MATCH_STATE);
            runDynamicAiAnalysis(CURRENT_MATCH_STATE);
        }

        function updateMatchView(state) {
            if (!state) return;

            document.getElementById('p-ko-count').textContent = state.player.prizes_taken || 0;
            document.getElementById('opp-ko-count').textContent = state.opponent.prizes_taken || 0;
            document.getElementById('p-deck-count').textContent = (state.player.deck || []).length;

            const drawBtn = document.getElementById('btn-claim-deck-card');
            if (drawBtn) {
                const deckCount = (state.player.deck || []).length;
                if (state.card_drawn_this_turn) {
                    drawBtn.disabled = true;
                    drawBtn.style.opacity = '0.5';
                    drawBtn.style.cursor = 'not-allowed';
                    drawBtn.innerHTML = `🃏 DECK CARD DRAWN (<span id="p-deck-count">${deckCount}</span> REMAINING)`;
                } else if (!state.is_player_turn || IS_AI_PROCESSING) {
                    drawBtn.disabled = true;
                    drawBtn.style.opacity = '0.5';
                    drawBtn.style.cursor = 'not-allowed';
                    drawBtn.innerHTML = `🃏 DRAW DECK CARD (<span id="p-deck-count">${deckCount}</span> REMAINING)`;
                } else {
                    drawBtn.disabled = false;
                    drawBtn.style.opacity = '1';
                    drawBtn.style.cursor = 'pointer';
                    drawBtn.innerHTML = `🃏 DRAW DECK CARD (<span id="p-deck-count">${deckCount}</span> REMAINING)`;
                }
            }

            const energyBtn = document.getElementById('btn-add-energy-main');
            if (energyBtn) {
                if (state.energy_attached_this_turn) {
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


            renderActiveCard('player-active-view', state.player.active_spot, true);
            renderActiveCard('opp-active-view', state.opponent.active_spot, false);
            renderBenchGrid('player-bench-view', state.player.bench, true);
            renderBenchGrid('opp-bench-view', state.opponent.bench, false);
            renderHandGrid(state.player.hand);
            renderCombatLog(state.match_log || []);

            const banner = document.getElementById('match-status-banner');
            if (banner) {
                if (state.winner) {
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

        function getCardImageUrl(meta, cardName) {
            if (meta && meta.image) return meta.image;
            const cname = (cardName || (meta ? meta.name : '')).toLowerCase().trim();
            const cleanName = cname.replace(/ ex$/, '').replace(/ v$/, '').trim();

            const POKEDEX_MAP = {
                'bulbasaur': 1, 'ivysaur': 2, 'venusaur': 3,
                'charmander': 4, 'charmeleon': 5, 'charizard': 6,
                'squirtle': 7, 'wartortle': 8, 'blastoise': 9,
                'caterpie': 10, 'metapod': 11, 'butterfree': 12,
                'pikachu': 25, 'raichu': 26,
                'jigglypuff': 39, 'wigglytuff': 40,
                'machop': 66, 'machoke': 67, 'machamp': 68,
                'gengar': 94, 'onix': 95,
                'eevee': 133, 'vaporeon': 134, 'jolteon': 135, 'flareon': 136,
                'snorlax': 143, 'articuno': 144, 'zapdos': 145, 'moltres': 146,
                'dratini': 147, 'dragonair': 148, 'dragonite': 149,
                'mewtwo': 150, 'mew': 151,
                'miraidon': 1008, 'koraidon': 1007,
                'potion': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/potion.png',
                'super potion': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/super-potion.png',
                'poke ball': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png',
                'ultra ball': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/ultra-ball.png',
                'switch': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/escape-rope.png'
            };

            for (let [k, v] of Object.entries(POKEDEX_MAP)) {
                if (cleanName.includes(k)) {
                    if (typeof v === 'number') {
                        return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${v}.png`;
                    }
                    return v;
                }
            }

            if (meta && meta.dataset_id) {
                const num = parseInt(String(meta.dataset_id).replace(/\D/g, ''));
                if (num && num >= 1 && num <= 1025) {
                    return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${num}.png`;
                }
            }

            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png`;
        }

        function renderActiveCard(containerId, pkmn, isPlayer) {
            const box = document.getElementById(containerId);
            if (!box || !pkmn) return;

            const meta = getCardMeta(pkmn.name);
            const maxHp = pkmn.max_hp || meta.hp || 100;
            const currHp = Math.max(0, pkmn.current_hp);
            const hpPct = Math.max(0, Math.min(100, (currHp / maxHp) * 100));
            const imgUrl = getCardImageUrl(meta, pkmn.name);
            const ptype = meta.pokemon_type || (meta.types && meta.types[0]) || 'Normal';

            let attacksHtml = '';
            const attacks = meta.attacks && meta.attacks.length > 0 ? meta.attacks : [{ name: "Strike", base_damage: 40, cost: ["Colorless"] }];
            attacks.forEach(atk => {
                let strikeBtn = '';
                if (isPlayer) {
                    const isTurn = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.is_player_turn && !IS_AI_PROCESSING && !CURRENT_MATCH_STATE.winner;
                    strikeBtn = `<button class="btn-cyber-sm" ${!isTurn ? 'disabled style="opacity:0.4; cursor:not-allowed;"' : ''} onclick="matchAttack('${atk.name.replace(/'/g, "\\'")}', ${atk.base_damage || 30})" style="padding:4px 8px; font-size:0.7rem;">⚡ STRIKE</button>`;
                }

                attacksHtml += `
                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.04); padding:4px 8px; border-radius:4px; margin-top:4px;">
                        <div>
                            <div style="font-weight:800; font-size:0.78rem;">${atk.name}</div>
                            <div style="font-size:0.65rem; color:var(--text-dim);">Cost: ${(atk.cost || ['Colorless']).join('/')}</div>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <b style="color:var(--neon-amber); font-size:0.8rem;">${atk.base_damage ? atk.base_damage + ' DMG' : 'Effect'}</b>
                            ${strikeBtn}
                        </div>
                    </div>
                `;
            });

            const energyDisplay = (pkmn.attached_energy && pkmn.attached_energy.length > 0)
                ? pkmn.attached_energy.map(e => `<span style="background:rgba(0,243,255,0.15); border:1px solid var(--neon-cyan); border-radius:3px; padding:1px 5px; font-size:0.65rem; margin-right:3px;">⚡ ${e}</span>`).join('')
                : '<span style="color:var(--text-dim); font-size:0.7rem;">None Attached</span>';

            box.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="font-family:var(--font-orbitron); font-size:0.92rem; color:${isPlayer ? 'var(--neon-cyan)' : 'var(--neon-magenta)'}; font-weight:900;">
                        ${isPlayer ? '👑 YOUR' : '👑 OPPONENT'} ACTIVE: ${pkmn.name}
                    </div>
                    <span class="cyber-badge" style="font-size:0.65rem; padding:2px 6px;">${ptype}</span>
                </div>

                <div style="display:flex; gap:12px; align-items:flex-start;">
                    <!-- Main Pokemon Card Image -->
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
            if (!bench || bench.length === 0) {
                box.innerHTML = `<div style="color:var(--text-dim); font-size:0.7rem; font-style:italic;">Empty Bench</div>`;
                return;
            }
            box.innerHTML = bench.map((b, i) => {
                const maxHp = b.max_hp || 70;
                const currHp = Math.max(0, b.current_hp);
                const meta = getCardMeta(b.name);
                const thumbUrl = getCardImageUrl(meta, b.name);
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
                            <div style="font-size:0.62rem; color:var(--text-dim); margin-top:2px;">Type: ${meta.pokemon_type || 'Basic'}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function renderHandGrid(hand) {
            const box = document.getElementById('player-hand-view');
            if (!box) return;
            const isTurn = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.is_player_turn && !IS_AI_PROCESSING && !CURRENT_MATCH_STATE.winner;

            if (!hand || hand.length === 0) {
                box.innerHTML = '<div style="color:var(--text-dim); font-size:0.75rem;">Your hand is empty. Click [DRAW DECK CARD] to draw!</div>';
                return;
            }

            box.innerHTML = hand.map(item => {
                const cname = typeof item === 'string' ? item : item.name;
                const meta = getCardMeta(cname);
                return `
                    <div style="background:rgba(8,14,28,0.9); border:1px solid rgba(0,243,255,0.3); border-radius:6px; padding:5px 8px; display:inline-flex; align-items:center; gap:8px; font-size:0.75rem;">
                        <div>
                            <div style="font-weight:800; color:#fff;">${cname}</div>
                            <div style="font-size:0.65rem; color:var(--neon-cyan);">${meta.hp ? meta.hp + ' HP' : (meta.card_type || 'Card')}</div>
                        </div>
                        <button class="btn-cyber-sm" style="padding:3px 6px; font-size:0.68rem;" ${!isTurn ? 'disabled style="opacity:0.4;"' : ''} onclick="matchPlayCard('${cname.replace(/'/g, "\\'")}')">Play</button>
                    </div>
                `;
            }).join('');
        }

        function renderCombatLog(log) {
            const box = document.getElementById('combat-log');
            if (!box) return;
            box.innerHTML = (log || []).map(l => `<div>&gt; ${l}</div>`).join('');
            box.scrollTop = box.scrollHeight;
        }

        function claimRandomDeckCard() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            if (!CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) {
                alert("⏳ Please wait! It is the Opponent AI's turn.");
                return;
            }
            if (CURRENT_MATCH_STATE.card_drawn_this_turn) {
                alert("⚠️ You can only draw 1 deck card per turn!");
                return;
            }
            if (!CURRENT_MATCH_STATE.player.deck || CURRENT_MATCH_STATE.player.deck.length === 0) {
                alert("⚠️ Your deck is out of cards!");
                return;
            }
            const drawn = CURRENT_MATCH_STATE.player.deck.pop();
            CURRENT_MATCH_STATE.player.hand.push(drawn);
            CURRENT_MATCH_STATE.card_drawn_this_turn = true;
            CURRENT_MATCH_STATE.match_log.push(`🃏 Drew [${drawn}] from your collection deck.`);
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

        function promptAddEnergyDirect(target) {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            if (!CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) {
                alert("⏳ Please wait! It is the Opponent AI's turn.");
                return;
            }
            if (CURRENT_MATCH_STATE.energy_attached_this_turn) {
                alert("⚡ Energy Rule: You can only attach 1 energy from hand per turn!");
                return;
            }
            const pActive = CURRENT_MATCH_STATE.player.active_spot;
            const limit = getPokemonMaxEnergyLimit(pActive.name);
            const currentEnergy = (pActive.attached_energy || []).length;
            if (currentEnergy >= limit) {
                alert(`⚠️ Energy Limit: [${pActive.name}] already has ${currentEnergy} energy attached (max saturation limit: ${limit}).`);
                return;
            }

            pActive.attached_energy.push("Basic Energy");
            CURRENT_MATCH_STATE.energy_attached_this_turn = true;
            CURRENT_MATCH_STATE.match_log.push(`⚡ Attached 1 Energy to active [${pActive.name}] (${pActive.attached_energy.length}/${limit}).`);

            advanceWinningRouteStepIfType("ATTACH_ENERGY");
            updateMatchView(CURRENT_MATCH_STATE);
            if (LAST_AI_REPORT) {
                renderStrategicAiReport(LAST_AI_REPORT);
            }
        }

        function matchPlayCard(cname) {
            if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) return;
            const hand = CURRENT_MATCH_STATE.player.hand || [];
            const idx = hand.indexOf(cname);
            if (idx === -1) return;

            const clean = cname.toLowerCase().trim();
            const meta = getCardMeta(cname);
            const stype = (meta.card_type || meta.supertype || '').toLowerCase();
            const stage = meta.stage || '';

            const isEnergy = stype.includes('energy') || clean.includes('energy');
            const isTrainer = stype.includes('trainer') || stype.includes('item') || stype.includes('supporter') ||
                clean.includes('potion') || clean.includes('research') || clean.includes('ball') || clean.includes('switch') || clean.includes('boss') || clean.includes('rope');

            // 1. Trainer / Item / Supporter
            if (isTrainer) {
                hand.splice(idx, 1);
                // 1A. Potion / Healing Items
                if (clean.includes('potion')) {
                    const healAmt = clean.includes('super') ? 60 : 30;
                    const pActive = CURRENT_MATCH_STATE.player.active_spot;
                    const oldHp = pActive.current_hp;
                    pActive.current_hp = Math.min(pActive.max_hp || 70, (pActive.current_hp || 0) + healAmt);
                    const healed = pActive.current_hp - oldHp;
                    CURRENT_MATCH_STATE.match_log.push(`💊 Played [${cname}] from hand: Healed ${healed} HP on active [${pActive.name}] (${pActive.current_hp}/${pActive.max_hp}).`);
                    advanceWinningRouteStepIfType("PLAY_ITEM");
                }
                // 1B. Research / Draw Cards
                else if (clean.includes('research') || clean.includes('draw') || clean.includes('iono') || clean.includes('cheren')) {
                    let drawnCards = [];
                    for (let i = 0; i < 2; i++) {
                        if (CURRENT_MATCH_STATE.player.deck && CURRENT_MATCH_STATE.player.deck.length > 0) {
                            drawnCards.push(CURRENT_MATCH_STATE.player.deck.pop());
                        }
                    }
                    CURRENT_MATCH_STATE.player.hand.push(...drawnCards);
                    CURRENT_MATCH_STATE.match_log.push(`📜 Played [${cname}] from hand: Drew ${drawnCards.length} cards into hand!`);
                    advanceWinningRouteStepIfType("PLAY_SUPPORTER");
                }
                // 1C. Ball / Search Cards
                else if (clean.includes('ball')) {
                    const deck = CURRENT_MATCH_STATE.player.deck || [];
                    const bIdx = deck.findIndex(c => isBasicPokemon(getCardMeta(c)));
                    if (bIdx !== -1) {
                        const found = deck.splice(bIdx, 1)[0];
                        CURRENT_MATCH_STATE.player.hand.push(found);
                        CURRENT_MATCH_STATE.match_log.push(`🎾 Played [${cname}] from hand: Searched collection deck for Basic [${found}] and added to hand!`);
                    } else {
                        CURRENT_MATCH_STATE.match_log.push(`🎾 Played [${cname}] from hand: Searched deck, but no Basic Pokémon found.`);
                    }
                    advanceWinningRouteStepIfType("PLAY_ITEM");
                }
                // 1D. Switch / Escape Rope
                else if (clean.includes('switch') || clean.includes('rope')) {
                    const bench = CURRENT_MATCH_STATE.player.bench || [];
                    if (bench.length > 0) {
                        const oldActive = CURRENT_MATCH_STATE.player.active_spot;
                        let targetIdx = 0;
                        if (LAST_AI_REPORT && LAST_AI_REPORT.winning_route && LAST_AI_REPORT.winning_route.steps) {
                            const curStep = LAST_AI_REPORT.winning_route.steps[CURRENT_ROUTE_STEP_INDEX];
                            if (curStep && curStep.target_pokemon) {
                                const fIdx = bench.findIndex(b => b.name.toLowerCase() === curStep.target_pokemon.toLowerCase());
                                if (fIdx !== -1) targetIdx = fIdx;
                            }
                        }
                        const newActive = bench.splice(targetIdx, 1)[0];
                        CURRENT_MATCH_STATE.player.active_spot = {
                            name: newActive.name,
                            current_hp: newActive.current_hp,
                            max_hp: newActive.max_hp,
                            attached_energy: newActive.attached_energy || []
                        };
                        bench.push({
                            name: oldActive.name,
                            current_hp: oldActive.current_hp,
                            max_hp: oldActive.max_hp,
                            attached_energy: oldActive.attached_energy || []
                        });
                        CURRENT_MATCH_STATE.match_log.push(`🔄 Played [${cname}] from hand: Switched active [${oldActive.name}] with [${newActive.name}] from bench to exploit matchup!`);
                    } else {
                        CURRENT_MATCH_STATE.match_log.push(`🔄 Played [${cname}] from hand: No benched Pokémon available to switch.`);
                    }
                    advanceWinningRouteStepIfType("PLAY_ITEM");
                }
                // 1E. Boss's Orders / Gust
                else if (clean.includes('boss') || clean.includes('gust')) {
                    const oppBench = CURRENT_MATCH_STATE.opponent.bench || [];
                    if (oppBench.length > 0) {
                        let targetIdx = 0;
                        if (LAST_AI_REPORT && LAST_AI_REPORT.winning_route && LAST_AI_REPORT.winning_route.steps) {
                            const curStep = LAST_AI_REPORT.winning_route.steps[CURRENT_ROUTE_STEP_INDEX];
                            if (curStep && curStep.target_pokemon) {
                                const fIdx = oppBench.findIndex(b => b.name.toLowerCase() === curStep.target_pokemon.toLowerCase());
                                if (fIdx !== -1) targetIdx = fIdx;
                            }
                        }
                        const oldOpp = CURRENT_MATCH_STATE.opponent.active_spot;
                        const newOpp = oppBench.splice(targetIdx, 1)[0];
                        CURRENT_MATCH_STATE.opponent.active_spot = {
                            name: newOpp.name,
                            current_hp: newOpp.current_hp,
                            max_hp: newOpp.max_hp,
                            attached_energy: newOpp.attached_energy || []
                        };
                        oppBench.push({
                            name: oldOpp.name,
                            current_hp: oldOpp.current_hp,
                            max_hp: oldOpp.max_hp,
                            attached_energy: oldOpp.attached_energy || []
                        });
                        CURRENT_MATCH_STATE.match_log.push(`🎯 Played [${cname}] from hand: Forced opponent to promote bench [${newOpp.name}] to Active!`);
                    } else {
                        CURRENT_MATCH_STATE.match_log.push(`🎯 Played [${cname}] from hand: Opponent has no benched Pokémon to switch.`);
                    }
                    advanceWinningRouteStepIfType("PLAY_SUPPORTER");
                }
                // Generic Trainer fallback
                else {
                    CURRENT_MATCH_STATE.match_log.push(`📜 Played Trainer card [${cname}] from hand.`);
                    advanceWinningRouteStepIfType("PLAY_ITEM");
                }

                if (LAST_AI_REPORT) {
                    renderStrategicAiReport(LAST_AI_REPORT);
                }
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }

            // 2. Energy Card
            if (isEnergy) {
                if (CURRENT_MATCH_STATE.energy_attached_this_turn) {
                    alert("⚡ Energy Rule: You can only attach 1 energy from hand per turn!");
                    return;
                }
                const pActive = CURRENT_MATCH_STATE.player.active_spot;
                const limit = getPokemonMaxEnergyLimit(pActive.name);
                const currentEnergy = (pActive.attached_energy || []).length;
                if (currentEnergy >= limit) {
                    alert(`⚠️ Energy Limit: [${pActive.name}] already has ${currentEnergy} energy attached (max saturation limit: ${limit}).`);
                    return;
                }
                hand.splice(idx, 1);
                pActive.attached_energy.push(cname);
                CURRENT_MATCH_STATE.energy_attached_this_turn = true;
                CURRENT_MATCH_STATE.match_log.push(`⚡ Attached [${cname}] to active [${pActive.name}] (${pActive.attached_energy.length}/${limit}).`);
                advanceWinningRouteStepIfType("ATTACH_ENERGY");
                if (LAST_AI_REPORT) {
                    renderStrategicAiReport(LAST_AI_REPORT);
                }
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }

            // 3. Evolution Pokemon -> Must evolve onto matching Pokemon
            if (stage === 'Stage 1' || stage === 'Stage 2' || (meta.evolves_from && meta.evolves_from.length > 0)) {
                const evoFrom = (meta.evolves_from || '').toLowerCase();
                const pActive = CURRENT_MATCH_STATE.player.active_spot;
                let evolved = false;

                if (evoFrom && pActive.name.toLowerCase().includes(evoFrom)) {
                    hand.splice(idx, 1);
                    pActive.name = cname;
                    pActive.max_hp = meta.hp || 120;
                    pActive.current_hp = pActive.max_hp;
                    CURRENT_MATCH_STATE.match_log.push(`🔥 Evolved Active into [${cname}]! (HP: ${pActive.max_hp}).`);
                    evolved = true;
                } else {
                    const bench = CURRENT_MATCH_STATE.player.bench || [];
                    for (let b of bench) {
                        if (evoFrom && b.name.toLowerCase().includes(evoFrom)) {
                            hand.splice(idx, 1);
                            b.name = cname;
                            b.max_hp = meta.hp || 100;
                            b.current_hp = b.max_hp;
                            CURRENT_MATCH_STATE.match_log.push(`🔥 Evolved Benched Pokémon into [${cname}]!`);
                            evolved = true;
                            break;
                        }
                    }
                }
                if (!evolved) {
                    alert(`⚠️ Cannot evolve: [${cname}] evolves from [${meta.evolves_from || 'Pre-evolution'}], which is not on your active or bench spots!`);
                    return;
                }
                advanceWinningRouteStepIfType("EVOLVE_POKEMON");
                if (LAST_AI_REPORT) {
                    renderStrategicAiReport(LAST_AI_REPORT);
                }
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }

            // 4. Basic Pokemon -> Bench
            if (isBasicPokemon(meta)) {
                const bench = CURRENT_MATCH_STATE.player.bench || [];
                if (bench.length >= 3) {
                    alert("⚠️ Bench is full (max 3 Pokémon slots)!");
                    return;
                }
                hand.splice(idx, 1);
                bench.push({ name: cname, current_hp: meta.hp || 70, max_hp: meta.hp || 70, attached_energy: [] });
                CURRENT_MATCH_STATE.match_log.push(`🛡️ Placed Basic Pokémon [${cname}] onto Bench.`);
                advanceWinningRouteStepIfType("BENCH_POKEMON");
                if (LAST_AI_REPORT) {
                    renderStrategicAiReport(LAST_AI_REPORT);
                }
                updateMatchView(CURRENT_MATCH_STATE);
                return;
            }
        }

        function matchAttack(atkName, dmg) {
            if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING) return;

            const pActive = CURRENT_MATCH_STATE.player.active_spot;
            const oppActive = CURRENT_MATCH_STATE.opponent.active_spot;

            oppActive.current_hp = Math.max(0, oppActive.current_hp - dmg);
            CURRENT_MATCH_STATE.match_log.push(`⚔️ Your [${pActive.name}] used [${atkName}] for ${dmg} DMG! (Opponent HP: ${oppActive.current_hp}/${oppActive.max_hp})`);

            if (oppActive.current_hp <= 0) {
                CURRENT_MATCH_STATE.player.prizes_taken = (CURRENT_MATCH_STATE.player.prizes_taken || 0) + 1;
                CURRENT_MATCH_STATE.match_log.push(`🔥 Opponent's [${oppActive.name}] was KNOCKED OUT! Prize (${CURRENT_MATCH_STATE.player.prizes_taken}/3)!`);

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
                }
            }

            updateMatchView(CURRENT_MATCH_STATE);
            endPlayerTurn();
        }

        function endPlayerTurn() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner || IS_AI_PROCESSING) return;
            CURRENT_MATCH_STATE.is_player_turn = false;
            CURRENT_MATCH_STATE.match_log.push(`--- Opponent AI Turn ---`);
            updateMatchView(CURRENT_MATCH_STATE);
            executeAiTurn();
        }

        async function executeAiTurn() {
            if (!CURRENT_MATCH_STATE || CURRENT_MATCH_STATE.winner) return;
            IS_AI_PROCESSING = true;

            const sleep = (ms) => new Promise(r => setTimeout(r, ms));
            await sleep(700);

            if (CURRENT_MATCH_STATE.opponent.deck && CURRENT_MATCH_STATE.opponent.deck.length > 0) {
                const drawn = CURRENT_MATCH_STATE.opponent.deck.pop();
                CURRENT_MATCH_STATE.opponent.hand.push(drawn);
                CURRENT_MATCH_STATE.match_log.push(`🤖 Opponent AI drew 1 card.`);
            }

            CURRENT_MATCH_STATE.opponent.active_spot.attached_energy.push("Basic Lightning Energy");
            CURRENT_MATCH_STATE.match_log.push(`🤖 Opponent attached Energy to [${CURRENT_MATCH_STATE.opponent.active_spot.name}].`);
            updateMatchView(CURRENT_MATCH_STATE);

            await sleep(700);

            const pActive = CURRENT_MATCH_STATE.player.active_spot;
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
                    const promoted = pBench.shift();
                    CURRENT_MATCH_STATE.player.active_spot = {
                        name: promoted.name,
                        current_hp: promoted.max_hp || 70,
                        max_hp: promoted.max_hp || 70,
                        attached_energy: []
                    };
                    CURRENT_MATCH_STATE.match_log.push(`🔄 You promoted [${promoted.name}] to Active Spot.`);
                }
            }

            CURRENT_MATCH_STATE.is_player_turn = true;
            CURRENT_MATCH_STATE.card_drawn_this_turn = false;
            CURRENT_MATCH_STATE.energy_attached_this_turn = false;
            CURRENT_ROUTE_STEP_INDEX = 0;
            CURRENT_MATCH_STATE.turn_number++;
            CURRENT_MATCH_STATE.match_log.push(`--- Turn ${CURRENT_MATCH_STATE.turn_number}: Your Turn ---`);

            // Automatic Turn-Start Deck Draw per official Pokemon TCG rules!
            if (CURRENT_MATCH_STATE.player.deck && CURRENT_MATCH_STATE.player.deck.length > 0) {
                const drawnCard = CURRENT_MATCH_STATE.player.deck.pop();
                CURRENT_MATCH_STATE.player.hand.push(drawnCard);
                CURRENT_MATCH_STATE.card_drawn_this_turn = true;
                CURRENT_MATCH_STATE.match_log.push(`🎴 Turn ${CURRENT_MATCH_STATE.turn_number} Start Draw: Took 1 card [${drawnCard}] from deck into hand.`);
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
                const payload = {
                    game_state: {
                        turn_number: CURRENT_MATCH_STATE.turn_number || 1,
                        is_player_turn: CURRENT_MATCH_STATE.is_player_turn,
                        player: {
                            active_spot: {
                                name: CURRENT_MATCH_STATE.player.active_spot.name,
                                current_hp: CURRENT_MATCH_STATE.player.active_spot.current_hp,
                                max_hp: CURRENT_MATCH_STATE.player.active_spot.max_hp,
                                attached_energy: CURRENT_MATCH_STATE.player.active_spot.attached_energy || []
                            },
                            active_pokemon: {
                                name: CURRENT_MATCH_STATE.player.active_spot.name,
                                current_hp: CURRENT_MATCH_STATE.player.active_spot.current_hp,
                                max_hp: CURRENT_MATCH_STATE.player.active_spot.max_hp,
                                attached_energy: CURRENT_MATCH_STATE.player.active_spot.attached_energy || []
                            },
                            bench: (CURRENT_MATCH_STATE.player.bench || []).map(b => ({
                                name: b.name,
                                current_hp: b.current_hp,
                                max_hp: b.max_hp,
                                attached_energy: b.attached_energy || []
                            })),
                            hand: CURRENT_MATCH_STATE.player.hand || [],
                            deck_count: (CURRENT_MATCH_STATE.player.deck || []).length,
                            prizes_remaining: Math.max(1, 6 - (CURRENT_MATCH_STATE.player.prizes_taken || 0)),
                            prizes_taken: CURRENT_MATCH_STATE.player.prizes_taken || 0
                        },
                        opponent: {
                            active_spot: {
                                name: CURRENT_MATCH_STATE.opponent.active_spot.name,
                                current_hp: CURRENT_MATCH_STATE.opponent.active_spot.current_hp,
                                max_hp: CURRENT_MATCH_STATE.opponent.active_spot.max_hp,
                                attached_energy: CURRENT_MATCH_STATE.opponent.active_spot.attached_energy || []
                            },
                            active_pokemon: {
                                name: CURRENT_MATCH_STATE.opponent.active_spot.name,
                                current_hp: CURRENT_MATCH_STATE.opponent.active_spot.current_hp,
                                max_hp: CURRENT_MATCH_STATE.opponent.active_spot.max_hp,
                                attached_energy: CURRENT_MATCH_STATE.opponent.active_spot.attached_energy || []
                            },
                            bench: (CURRENT_MATCH_STATE.opponent.bench || []).map(b => ({
                                name: b.name,
                                current_hp: b.current_hp,
                                max_hp: b.max_hp,
                                attached_energy: b.attached_energy || []
                            })),
                            hand_count: (CURRENT_MATCH_STATE.opponent.hand || []).length,
                            deck_count: (CURRENT_MATCH_STATE.opponent.deck || []).length,
                            prizes_remaining: Math.max(1, 6 - (CURRENT_MATCH_STATE.opponent.prizes_taken || 0)),
                            prizes_taken: CURRENT_MATCH_STATE.opponent.prizes_taken || 0
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
                    mathFormElem.textContent = data.mathematical_calculations.formula || 'Damage = (Base + Bonus) * Weakness - Resist';
                }
                if (mathEvElem) {
                    const ev = data.mathematical_calculations.expected_value_ev;
                    const ko = data.mathematical_calculations.knockout_probability_pct;
                    const risk = data.risk_assessment ? data.risk_assessment.risk_level : 'LOW';
                    mathEvElem.textContent = `EV: ${ev >= 0 ? '+' : ''}${ev} • KO Chance: ${ko} • Risk: ${risk}`;
                }
            }
        }

        function executeAiRecommendation() {
            if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.is_player_turn || IS_AI_PROCESSING || CURRENT_MATCH_STATE.winner) return;

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
                        let cardToPlay = targetCard && pHand.includes(targetCard) ? targetCard : pHand.find(c => {
                            const meta = getCardMeta(c);
                            const stype = (meta.card_type || meta.supertype || '').toLowerCase();
                            return stype.includes('trainer') || stype.includes('item') || stype.includes('supporter') ||
                                   c.toLowerCase().includes('potion') || c.toLowerCase().includes('research') || c.toLowerCase().includes('ball') ||
                                   c.toLowerCase().includes('switch') || c.toLowerCase().includes('rope') || c.toLowerCase().includes('boss');
                        });

                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        if (cardToPlay) {
                            matchPlayCard(cardToPlay);
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
                        let cardToPlay = targetCard && pHand.includes(targetCard) ? targetCard : pHand.find(c => {
                            const meta = getCardMeta(c);
                            return (meta.stage === 'Stage 1' || meta.stage === 'Stage 2');
                        });

                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        if (cardToPlay) {
                            matchPlayCard(cardToPlay);
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
                        let cardToPlay = targetCard && pHand.includes(targetCard) ? targetCard : pHand.find(c => isBasicPokemon(getCardMeta(c)));

                        const prevIdx = CURRENT_ROUTE_STEP_INDEX;
                        if (cardToPlay) {
                            matchPlayCard(cardToPlay);
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
                        promptAddEnergyDirect('player');
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
                        matchAttack(atkName, dmg);
                        return; // Turn concludes
                    }
                }
            }

            // Fallback: Primary attack
            const meta = getCardMeta(CURRENT_MATCH_STATE.player.active_spot.name);
            const atk = (meta.attacks && meta.attacks[0]) ? meta.attacks[0] : { name: "Strike", base_damage: 40 };
            matchAttack(atk.name, atk.base_damage || 40);
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
            await checkAuthSession();
            startNewMatch();
        });
    </script>
</body>
</html>
"""
