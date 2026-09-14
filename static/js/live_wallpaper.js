/**
 * UNNATI Exams - Interactive Formal Live Wallpaper Engine
 * Features: Multi-frequency Harmonic Vector Waves, Dynamic Technical Grid,
 * Datum Crosshair Nodes, and Cursor Displacement Physics.
 */

(function () {
    const canvas = document.getElementById('interactive-wallpaper-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = window.devicePixelRatio || 1;
    let animId = null;
    let time = 0;

    // Non-interactive pointer state
    const pointer = {
        x: -9999,
        y: -9999,
        targetX: -9999,
        targetY: -9999,
        radius: 200,
        active: false,
        intensity: 0
    };

    // Interactive click shockwaves / ripples (Disabled)
    const ripples = [];

    // Technical Grid Configuration
    const GRID_SPACING = 80;
    const gridPoints = [];

    // Formal Harmonic Wave Layers (Tone down opacity & amplitude for subtle, elegant background)
    const waveLayers = [
        {
            baseYRatio: 0.72,
            amplitude: 22,
            frequency: 0.0012,
            speed: 0.008,
            color: 'rgba(255, 107, 53, 0.16)',
            fillGrad: ['rgba(255, 107, 53, 0.025)', 'transparent'],
            lineWidth: 1.2,
            phaseOffset: 0
        },
        {
            baseYRatio: 0.68,
            amplitude: 18,
            frequency: 0.0015,
            speed: -0.006,
            color: 'rgba(247, 147, 30, 0.12)',
            fillGrad: ['rgba(247, 147, 30, 0.015)', 'transparent'],
            lineWidth: 1.0,
            phaseOffset: 1.8
        },
        {
            baseYRatio: 0.60,
            amplitude: 25,
            frequency: 0.0010,
            speed: 0.005,
            color: 'rgba(59, 130, 246, 0.14)',
            fillGrad: ['rgba(59, 130, 246, 0.02)', 'transparent'],
            lineWidth: 1.1,
            phaseOffset: 3.4
        },
        {
            baseYRatio: 0.54,
            amplitude: 16,
            frequency: 0.0018,
            speed: -0.008,
            color: 'rgba(255, 128, 66, 0.10)',
            fillGrad: ['rgba(255, 107, 53, 0.01)', 'transparent'],
            lineWidth: 0.9,
            phaseOffset: 5.1
        },
        {
            baseYRatio: 0.45,
            amplitude: 14,
            frequency: 0.0012,
            speed: 0.006,
            color: 'rgba(148, 163, 184, 0.08)',
            fillGrad: ['rgba(148, 163, 184, 0.01)', 'transparent'],
            lineWidth: 0.8,
            phaseOffset: 2.2
        }
    ];

    // Formal Technical Datum Markers (crosshairs, reticles)
    const datumMarkers = [];

    function initDatumMarkers() {
        datumMarkers.length = 0;
        const count = Math.floor((width * height) / 75000);
        for (let i = 0; i < count; i++) {
            datumMarkers.push({
                x: Math.random() * width,
                y: Math.random() * height,
                type: Math.floor(Math.random() * 4), // 0: crosshair, 1: corner brackets, 2: circle reticle, 3: diamond
                size: 5 + Math.random() * 4,
                baseAlpha: 0.06 + Math.random() * 0.08,
                alpha: 0.08,
                pulseOffset: Math.random() * Math.PI * 2,
                driftVx: (Math.random() - 0.5) * 0.05,
                driftVy: (Math.random() - 0.5) * 0.05
            });
        }
    }

    function initGrid() {
        gridPoints.length = 0;
        const cols = Math.ceil(width / GRID_SPACING) + 1;
        const rows = Math.ceil(height / GRID_SPACING) + 1;

        for (let r = 0; r <= rows; r++) {
            for (let c = 0; c <= cols; c++) {
                gridPoints.push({
                    baseX: c * GRID_SPACING,
                    baseY: r * GRID_SPACING,
                    x: c * GRID_SPACING,
                    y: r * GRID_SPACING,
                    glow: 0
                });
            }
        }
    }

    function handleResize() {
        width = window.innerWidth;
        height = window.innerHeight;
        dpr = window.devicePixelRatio || 1;

        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);

        initGrid();
        initDatumMarkers();
    }

    // Pointer / mouse interactive listeners removed for a clean, non-interactive formal backdrop.

    // Draw Formal Technical Grid
    // Draw Formal Technical Grid
    function drawGrid() {
        ctx.save();

        const cols = Math.ceil(width / GRID_SPACING) + 1;
        const rows = Math.ceil(height / GRID_SPACING) + 1;

        // 1. Subtle horizontal and vertical background grid lines (Batched)
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.035)';
        ctx.lineWidth = 0.6;
        for (let c = 0; c <= cols; c++) {
            const gx = c * GRID_SPACING;
            const distToMouse = pointer.active ? Math.abs(gx - pointer.x) : 9999;
            if (distToMouse >= pointer.radius) {
                ctx.moveTo(gx, 0);
                ctx.lineTo(gx, height);
            }
        }
        for (let r = 0; r <= rows; r++) {
            const gy = r * GRID_SPACING;
            const distToMouse = pointer.active ? Math.abs(gy - pointer.y) : 9999;
            if (distToMouse >= pointer.radius) {
                ctx.moveTo(0, gy);
                ctx.lineTo(width, gy);
            }
        }
        ctx.stroke();

        // Cursor proximity reactive lines
        if (pointer.active) {
            for (let c = 0; c <= cols; c++) {
                const gx = c * GRID_SPACING;
                const distToMouse = Math.abs(gx - pointer.x);
                if (distToMouse < pointer.radius) {
                    const proximity = (1 - distToMouse / pointer.radius) * 0.18;
                    ctx.beginPath();
                    ctx.moveTo(gx, 0);
                    ctx.lineTo(gx, height);
                    ctx.strokeStyle = `rgba(255, 107, 53, ${0.04 + proximity})`;
                    ctx.lineWidth = 1.0;
                    ctx.stroke();
                }
            }
            for (let r = 0; r <= rows; r++) {
                const gy = r * GRID_SPACING;
                const distToMouse = Math.abs(gy - pointer.y);
                if (distToMouse < pointer.radius) {
                    const proximity = (1 - distToMouse / pointer.radius) * 0.18;
                    ctx.beginPath();
                    ctx.moveTo(0, gy);
                    ctx.lineTo(width, gy);
                    ctx.strokeStyle = `rgba(255, 107, 53, ${0.04 + proximity})`;
                    ctx.lineWidth = 1.0;
                    ctx.stroke();
                }
            }
        }

        // 2. Grid Intersection Crosshairs (+) with Interactive Lens Glow (Batched)
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 0.8;
        const glowingPts = [];

        for (let i = 0; i < gridPoints.length; i++) {
            const pt = gridPoints[i];

            if (pointer.active) {
                const dx = pt.baseX - pointer.x;
                const dy = pt.baseY - pointer.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < pointer.radius && dist > 1) {
                    const force = 1 - dist / pointer.radius;
                    pt.x = pt.baseX + (dx / dist) * force * 10;
                    pt.y = pt.baseY + (dy / dist) * force * 10;
                    pt.glow = Math.min(1, pt.glow + force * 0.4);
                } else {
                    pt.x = pt.baseX;
                    pt.y = pt.baseY;
                }
            } else {
                pt.x = pt.baseX;
                pt.y = pt.baseY;
            }

            pt.glow *= 0.92;

            if (pt.glow > 0.05) {
                glowingPts.push(pt);
            } else {
                const crossSize = 3.5;
                ctx.moveTo(pt.x - crossSize, pt.y);
                ctx.lineTo(pt.x + crossSize, pt.y);
                ctx.moveTo(pt.x, pt.y - crossSize);
                ctx.lineTo(pt.x, pt.y + crossSize);
            }
        }
        ctx.stroke();

        // Draw only glowing crosshairs individually
        for (let i = 0; i < glowingPts.length; i++) {
            const pt = glowingPts[i];
            const crossSize = 3.5 + pt.glow * 3.0;
            const alpha = 0.12 + pt.glow * 0.65;
            ctx.beginPath();
            ctx.moveTo(pt.x - crossSize, pt.y);
            ctx.lineTo(pt.x + crossSize, pt.y);
            ctx.moveTo(pt.x, pt.y - crossSize);
            ctx.lineTo(pt.x, pt.y + crossSize);
            ctx.strokeStyle = `rgba(255, 107, 53, ${alpha})`;
            ctx.lineWidth = 1.2;
            ctx.stroke();
        }

        ctx.restore();
    }

    // Draw Formal Technical Datum Markers (Reticles, Brackets, Crosshairs)
    function drawDatumMarkers() {
        ctx.save();

        for (let i = 0; i < datumMarkers.length; i++) {
            const m = datumMarkers[i];
            m.x += m.driftVx;
            m.y += m.driftVy;

            // Boundary wrap
            if (m.x < -30) m.x = width + 30;
            if (m.x > width + 30) m.x = -30;
            if (m.y < -30) m.y = height + 30;
            if (m.y > height + 30) m.y = -30;

            // Distance to pointer
            let extraGlow = 0;
            if (pointer.active) {
                const dx = m.x - pointer.x;
                const dy = m.y - pointer.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < pointer.radius) {
                    extraGlow = (1 - dist / pointer.radius) * 0.7;
                }
            }

            const currentAlpha = Math.min(1, m.baseAlpha + extraGlow + Math.sin(time * 0.03 + m.pulseOffset) * 0.08);
            ctx.strokeStyle = extraGlow > 0
                ? `rgba(255, 107, 53, ${currentAlpha})`
                : `rgba(148, 163, 184, ${currentAlpha})`;
            ctx.fillStyle = ctx.strokeStyle;
            ctx.lineWidth = 1.0;

            const s = m.size * (1 + extraGlow * 0.25);

            ctx.beginPath();
            if (m.type === 0) {
                // Precision Circle Crosshair ⨁
                ctx.arc(m.x, m.y, s, 0, Math.PI * 2);
                ctx.moveTo(m.x - s * 1.5, m.y);
                ctx.lineTo(m.x + s * 1.5, m.y);
                ctx.moveTo(m.x, m.y - s * 1.5);
                ctx.lineTo(m.x, m.y + s * 1.5);
                ctx.stroke();
            } else if (m.type === 1) {
                // Corner Framing Brackets ⌜ ⌟
                const arm = s * 0.8;
                // Top-left
                ctx.moveTo(m.x - s, m.y - s + arm);
                ctx.lineTo(m.x - s, m.y - s);
                ctx.lineTo(m.x - s + arm, m.y - s);
                // Bottom-right
                ctx.moveTo(m.x + s, m.y + s - arm);
                ctx.lineTo(m.x + s, m.y + s);
                ctx.lineTo(m.x + s - arm, m.y + s);
                ctx.stroke();
            } else if (m.type === 2) {
                // Technical Diamond Node ⬦
                ctx.moveTo(m.x, m.y - s);
                ctx.lineTo(m.x + s, m.y);
                ctx.lineTo(m.x, m.y + s);
                ctx.lineTo(m.x - s, m.y);
                ctx.closePath();
                ctx.stroke();
                // Center dot
                ctx.beginPath();
                ctx.arc(m.x, m.y, 1.5, 0, Math.PI * 2);
                ctx.fill();
            } else {
                // Measurement tick cross
                ctx.moveTo(m.x - s * 1.2, m.y);
                ctx.lineTo(m.x + s * 1.2, m.y);
                ctx.moveTo(m.x, m.y - s * 1.2);
                ctx.lineTo(m.x, m.y + s * 1.2);
                ctx.stroke();
            }
        }

        ctx.restore();
    }

    // Draw Harmonic Continuous Vector Waveforms
    function drawWaves() {
        const step = 8; // Precision curve evaluation step in px

        for (let l = 0; l < waveLayers.length; l++) {
            const wave = waveLayers[l];
            const baseY = height * wave.baseYRatio;

            ctx.save();
            ctx.beginPath();
            ctx.moveTo(0, height);

            let firstY = baseY;

            for (let x = 0; x <= width + step; x += step) {
                // Harmonic sine series
                const waveArg1 = x * wave.frequency + time * wave.speed + wave.phaseOffset;
                const waveArg2 = x * (wave.frequency * 1.8) - time * (wave.speed * 0.7);
                const waveArg3 = x * (wave.frequency * 0.6) + time * (wave.speed * 1.3);

                let y = baseY +
                    Math.sin(waveArg1) * wave.amplitude +
                    Math.cos(waveArg2) * (wave.amplitude * 0.35) +
                    Math.sin(waveArg3) * (wave.amplitude * 0.2);

                // Pointer interactive displacement
                if (pointer.active) {
                    const dx = x - pointer.x;
                    const dy = y - pointer.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < pointer.radius * 1.4) {
                        const falloff = Math.exp(-((x - pointer.x) * (x - pointer.x)) / (2 * 75 * 75));
                        const pushDir = y > pointer.y ? 1 : -1;
                        y += falloff * 28 * pushDir;
                    }
                }

                // Ripple shockwave displacement
                for (let r = 0; r < ripples.length; r++) {
                    const rp = ripples[r];
                    const distFromCenter = Math.abs(x - rp.x);
                    const rippleDelta = Math.abs(distFromCenter - rp.radius);

                    if (rippleDelta < 50) {
                        const rippleFactor = (1 - rippleDelta / 50) * rp.alpha;
                        y += Math.sin((rippleDelta / 50) * Math.PI) * (rp.strength * 0.5) * rippleFactor;
                    }
                }

                if (x === 0) {
                    firstY = y;
                    ctx.lineTo(0, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }

            // Close wave path for bottom gradient fill
            ctx.lineTo(width, height);
            ctx.closePath();

            // Gradient Fill under the wave
            const fillGradient = ctx.createLinearGradient(0, baseY - wave.amplitude, 0, height);
            fillGradient.addColorStop(0, wave.fillGrad[0]);
            fillGradient.addColorStop(1, wave.fillGrad[1]);
            ctx.fillStyle = fillGradient;
            ctx.fill();

            // Draw clean crisp stroke along the wave crest
            ctx.beginPath();
            for (let x = 0; x <= width + step; x += step) {
                const waveArg1 = x * wave.frequency + time * wave.speed + wave.phaseOffset;
                const waveArg2 = x * (wave.frequency * 1.8) - time * (wave.speed * 0.7);
                const waveArg3 = x * (wave.frequency * 0.6) + time * (wave.speed * 1.3);

                let y = baseY +
                    Math.sin(waveArg1) * wave.amplitude +
                    Math.cos(waveArg2) * (wave.amplitude * 0.35) +
                    Math.sin(waveArg3) * (wave.amplitude * 0.2);

                if (pointer.active) {
                    const falloff = Math.exp(-((x - pointer.x) * (x - pointer.x)) / (2 * 75 * 75));
                    const pushDir = y > pointer.y ? 1 : -1;
                    y += falloff * 28 * pushDir;
                }

                for (let r = 0; r < ripples.length; r++) {
                    const rp = ripples[r];
                    const distFromCenter = Math.abs(x - rp.x);
                    const rippleDelta = Math.abs(distFromCenter - rp.radius);
                    if (rippleDelta < 50) {
                        const rippleFactor = (1 - rippleDelta / 50) * rp.alpha;
                        y += Math.sin((rippleDelta / 50) * Math.PI) * (rp.strength * 0.5) * rippleFactor;
                    }
                }

                if (x === 0) ctx.moveTo(0, y);
                else ctx.lineTo(x, y);
            }

            ctx.strokeStyle = wave.color;
            ctx.lineWidth = wave.lineWidth;
            ctx.stroke();

            ctx.restore();
        }
    }

    // Draw Click Ripples & Shockwaves
    function drawRipples() {
        for (let i = ripples.length - 1; i >= 0; i--) {
            const rp = ripples[i];
            rp.radius += rp.speed;
            rp.alpha *= 0.955;

            ctx.save();
            ctx.beginPath();
            ctx.arc(rp.x, rp.y, rp.radius, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(255, 107, 53, ${rp.alpha * 0.6})`;
            ctx.lineWidth = 1.5;
            ctx.shadowColor = '#FF6B35';
            ctx.shadowBlur = 10;
            ctx.stroke();
            ctx.restore();

            if (rp.radius >= rp.maxRadius || rp.alpha <= 0.02) {
                ripples.splice(i, 1);
            }
        }
    }

    // Interactive Cursor Spotlight / Atmospheric Beacon
    function drawPointerAura() {
        if (!pointer.active || pointer.x < -1000) return;

        ctx.save();
        const auraGrad = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, 180);
        auraGrad.addColorStop(0, 'rgba(255, 107, 53, 0.09)');
        auraGrad.addColorStop(0.5, 'rgba(247, 147, 30, 0.03)');
        auraGrad.addColorStop(1, 'transparent');

        ctx.fillStyle = auraGrad;
        ctx.beginPath();
        ctx.arc(pointer.x, pointer.y, 180, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    // Main 60 FPS Render Loop
    function animate() {
        // Pause heavy canvas redraws when a modal is open to keep inputs and modals responsive
        if (document.body.classList.contains('modal-open')) {
            animId = requestAnimationFrame(animate);
            return;
        }

        time += 1;

        // Smooth cursor interpolation
        if (pointer.active) {
            pointer.x += (pointer.targetX - pointer.x) * 0.15;
            pointer.y += (pointer.targetY - pointer.y) * 0.15;
        }

        ctx.clearRect(0, 0, width, height);

        // 1. Draw Technical Coordinate Grid
        drawGrid();

        // 2. Draw Formal Datum Markers (Reticles, Crosshairs)
        drawDatumMarkers();

        // 3. Draw Multi-Frequency Harmonic Vector Waveforms
        drawWaves();

        // 4. Draw Click Shockwave Ripples
        drawRipples();

        // 5. Draw Cursor Aura
        drawPointerAura();

        animId = requestAnimationFrame(animate);
    }

    // Lifecycle & Visibility
    window.addEventListener('resize', handleResize);
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            cancelAnimationFrame(animId);
        } else {
            animId = requestAnimationFrame(animate);
        }
    });

    // Initialize & Start
    handleResize();
    animId = requestAnimationFrame(animate);
})();
