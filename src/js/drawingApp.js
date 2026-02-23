document.addEventListener('DOMContentLoaded', function() {
    paper.setup('drawing-canvas');

    const CANVAS_PHYSICAL_WIDTH = 205;  // mm
    const CANVAS_PHYSICAL_HEIGHT = 73;  // mm

    const SMOOTHING_FACTOR = 10;

    let pathHistory = [];
    let currentPath = null;
    let isDrawing = false;

    const tool = new paper.Tool();

    tool.onMouseDown = function(event) {
        if (isWithinCanvasBounds(event.point)) {
            isDrawing = true;
            currentPath = new paper.Path();
            currentPath.strokeColor = 'black';
            currentPath.strokeWidth = 2;
            currentPath.strokeCap = 'round';
            currentPath.strokeJoin = 'round';
            currentPath.add(event.point);
        }
    };

    tool.onMouseDrag = function(event) {
        if (isDrawing && isWithinCanvasBounds(event.point)) {
            currentPath.add(event.point);
        }
    };

    tool.onMouseUp = function(event) {
        if (isDrawing) {
            currentPath.simplify(SMOOTHING_FACTOR);
            pathHistory.push(currentPath);
            isDrawing = false;
            currentPath = null;
            updateButtonStates();
        }
    };

    function isWithinCanvasBounds(point) {
        return point.x >= 0 && point.x <= paper.view.size.width &&
               point.y >= 0 && point.y <= paper.view.size.height;
    }

    function undoLastPath() {
        if (pathHistory.length > 0) {
            pathHistory.pop().remove();
            paper.view.update();
            updateButtonStates();
        }
    }

    function clearAll() {
        pathHistory.forEach(path => path.remove());
        pathHistory = [];
        paper.view.update();
        updateButtonStates();
    }

    function updateButtonStates() {
        const hasContent = pathHistory.length > 0;
        document.getElementById('undo-btn').disabled = !hasContent;
        document.getElementById('clear-btn').disabled = !hasContent;
        document.getElementById('save-btn').disabled = !hasContent;
    }

    function saveDrawing() {
        if (pathHistory.length === 0) return;

        const displayWidth = paper.view.size.width;
        const displayHeight = paper.view.size.height;
        const scaleX = CANVAS_PHYSICAL_WIDTH / displayWidth;
        const scaleY = CANVAS_PHYSICAL_HEIGHT / displayHeight;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        svg.setAttribute('width', CANVAS_PHYSICAL_WIDTH + 'mm');
        svg.setAttribute('height', CANVAS_PHYSICAL_HEIGHT + 'mm');
        svg.setAttribute('viewBox', `0 0 ${CANVAS_PHYSICAL_WIDTH} ${CANVAS_PHYSICAL_HEIGHT}`);

        const fmt = (v) => v.toFixed(3);
        const sx = (v) => fmt(v * scaleX);
        const sy = (v) => fmt(v * scaleY);

        pathHistory.forEach((path) => {
            const segs = path.segments;
            if (segs.length < 2) return;

            let d = `M ${sx(segs[0].point.x)},${sy(segs[0].point.y)}`;

            for (let i = 1; i < segs.length; i++) {
                const prev = segs[i - 1];
                const curr = segs[i];
                // Cubic bezier: control points are anchor + handle (handles are relative)
                const cp1x = sx(prev.point.x + prev.handleOut.x);
                const cp1y = sy(prev.point.y + prev.handleOut.y);
                const cp2x = sx(curr.point.x + curr.handleIn.x);
                const cp2y = sy(curr.point.y + curr.handleIn.y);
                d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${sx(curr.point.x)},${sy(curr.point.y)}`;
            }

            if (path.closed) d += ' Z';

            const svgPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            svgPath.setAttribute('d', d);
            svgPath.setAttribute('fill', 'none');
            svgPath.setAttribute('stroke', 'black');
            svgPath.setAttribute('stroke-width', '0.5');
            svg.appendChild(svgPath);
        });

        const blob = new Blob([new XMLSerializer().serializeToString(svg)], {type: 'image/svg+xml'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'mug-drawing.svg';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    document.getElementById('undo-btn').addEventListener('click', undoLastPath);
    document.getElementById('clear-btn').addEventListener('click', clearAll);
    document.getElementById('save-btn').addEventListener('click', saveDrawing);

    updateButtonStates();
    paper.view.update();
});
