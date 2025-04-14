document.addEventListener('DOMContentLoaded', function() {
    // Initialize Paper.js
    paper.setup('drawing-canvas');
    
    // Canvas physical dimensions (60mm x 150mm)
    const CANVAS_PHYSICAL_WIDTH = 60; // mm
    const CANVAS_PHYSICAL_HEIGHT = 150; // mm
    
    // Canvas display dimensions (600px x 240px - 10:4 ratio)
    const CANVAS_DISPLAY_WIDTH = 600;
    const CANVAS_DISPLAY_HEIGHT = 240;
    
    // Path styling
    const PATH_COLOR = 'black';
    const PATH_WIDTH = 2;
    
    // Store paths for undo functionality
    let pathHistory = [];
    let currentPath = null;
    let isDrawing = false;
    
    // Smoothing factor
    const SMOOTHING_FACTOR = 10;
    
    // Drawing tool setup
    const tool = new paper.Tool();
    
    // Mouse down event handler - start a new path
    tool.onMouseDown = function(event) {
        // Only draw if within canvas bounds
        if (isWithinCanvasBounds(event.point)) {
            isDrawing = true;
            
            // Create a new path
            currentPath = new paper.Path();
            currentPath.strokeColor = PATH_COLOR;
            currentPath.strokeWidth = PATH_WIDTH;
            currentPath.strokeCap = 'round';
            currentPath.strokeJoin = 'round';
            
            // Add the starting point
            currentPath.add(event.point);
        }
    };
    
    // Mouse drag event handler - continue the path
    tool.onMouseDrag = function(event) {
        if (isDrawing && isWithinCanvasBounds(event.point)) {
            // Add the current point to the path
            currentPath.add(event.point);
        }
    };
    
    // Mouse up event handler - finish the path
    tool.onMouseUp = function(event) {
        if (isDrawing) {
            // Finish the path
            currentPath.simplify(SMOOTHING_FACTOR);
            
            // Add to history for undo functionality
            pathHistory.push(currentPath);
            
            // Reset current state
            isDrawing = false;
            currentPath = null;
            
            // Update UI
            updateButtonStates();
        }
    };
    
    // Check if a point is within the canvas bounds
    function isWithinCanvasBounds(point) {
        return point.x >= 0 && point.x <= paper.view.size.width &&
               point.y >= 0 && point.y <= paper.view.size.height;
    }
    
    // Convert screen coordinates to physical dimensions (mm)
    function screenToPhysical(point) {
        return {
            x: (point.x / CANVAS_DISPLAY_WIDTH) * CANVAS_PHYSICAL_WIDTH,
            y: (point.y / CANVAS_DISPLAY_HEIGHT) * CANVAS_PHYSICAL_HEIGHT
        };
    }
    
    // Undo the last drawing
    function undoLastPath() {
        if (pathHistory.length > 0) {
            const lastPath = pathHistory.pop();
            lastPath.remove();
            paper.view.update();
            updateButtonStates();
        }
    }
    
    // Clear all drawings
    function clearAll() {
        // Remove all paths
        pathHistory.forEach(path => path.remove());
        pathHistory = [];
        paper.view.update();
        updateButtonStates();
    }
    
    // Update button states based on current drawing state
    function updateButtonStates() {
        document.getElementById('undo-btn').disabled = pathHistory.length === 0;
        document.getElementById('clear-btn').disabled = pathHistory.length === 0;
        document.getElementById('save-btn').disabled = pathHistory.length === 0;
        document.getElementById('upload-btn').disabled = pathHistory.length === 0;
    }
    
    // Save drawing as SVG
    function saveDrawing() {
        if (pathHistory.length === 0) return;
        
        // Create SVG container
        const svgContainer = document.createElement('div');
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', CANVAS_PHYSICAL_WIDTH);
        svg.setAttribute('height', CANVAS_PHYSICAL_HEIGHT);
        svg.setAttribute('viewBox', `0 0 ${CANVAS_PHYSICAL_WIDTH} ${CANVAS_PHYSICAL_HEIGHT}`);
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        svgContainer.appendChild(svg);
        
        // Scale factor to convert from display to physical coordinates
        const scaleX = CANVAS_PHYSICAL_WIDTH / CANVAS_DISPLAY_WIDTH;
        const scaleY = CANVAS_PHYSICAL_HEIGHT / CANVAS_DISPLAY_HEIGHT;

        // Add each path as an SVG path element
        const svgPaths = pathHistory.map((path, index) => {
            // Convert to SVG path format
            const svgPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            
            // Get path data string (d attribute) with physical coordinates
            const pathData = path.segments.map((segment, i) => {
                const x = segment.point.x * scaleX;
                const y = segment.point.y * scaleY;
                return i === 0 ? `M${x},${y}` : `L${x},${y}`;
            }).join(' ');
            
            svgPath.setAttribute('d', pathData);
            svgPath.setAttribute('fill', 'none');
            svgPath.setAttribute('stroke', 'black');
            svgPath.setAttribute('stroke-width', '0.5');
            svgPath.setAttribute('id', `path-${index}`);
            svg.appendChild(svgPath);
            
            return {
                id: `path-${index}`,
                d: pathData,
                order: index
            };
        });
        
        // Create an export object with SVG data
        const exportData = {
            svg: svgContainer.innerHTML,
            paths: svgPaths,
            canvasWidth: CANVAS_PHYSICAL_WIDTH,
            canvasHeight: CANVAS_PHYSICAL_HEIGHT,
            pathData: pathHistory.map((path, index) => {
                return {
                    id: `path-${index}`,
                    order: index,
                    svgPathData: svgPaths[index].d
                };
            })
        };
        
        // Create SVG file download
        const svgBlob = new Blob([svgContainer.innerHTML], {type: 'image/svg+xml'});
        const svgUrl = URL.createObjectURL(svgBlob);
        const svgLink = document.createElement('a');
        svgLink.href = svgUrl;
        svgLink.download = 'mug-drawing.svg';
        document.body.appendChild(svgLink);
        svgLink.click();
        document.body.removeChild(svgLink);
        URL.revokeObjectURL(svgUrl);
        
        // Also save path data in JSON format
        const jsonData = JSON.stringify(exportData, null, 2);
        const jsonBlob = new Blob([jsonData], {type: 'application/json'});
        const jsonUrl = URL.createObjectURL(jsonBlob);
        const jsonLink = document.createElement('a');
        jsonLink.href = jsonUrl;
        jsonLink.download = 'mug-drawing.json';
        document.body.appendChild(jsonLink);
        jsonLink.click();
        document.body.removeChild(jsonLink);
        URL.revokeObjectURL(jsonUrl);
    }
    
    // Upload drawing to server
    function uploadDrawing() {
        if (pathHistory.length === 0) return;
        
        // Scale factor to convert from display to physical coordinates
        const scaleX = CANVAS_PHYSICAL_WIDTH / CANVAS_DISPLAY_WIDTH;
        const scaleY = CANVAS_PHYSICAL_HEIGHT / CANVAS_DISPLAY_HEIGHT;
        
        // Create SVG container for upload
        const svgContainer = document.createElement('div');
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', CANVAS_PHYSICAL_WIDTH);
        svg.setAttribute('height', CANVAS_PHYSICAL_HEIGHT);
        svg.setAttribute('viewBox', `0 0 ${CANVAS_PHYSICAL_WIDTH} ${CANVAS_PHYSICAL_HEIGHT}`);
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        svgContainer.appendChild(svg);
        
        // Add each path as an SVG path element
        const svgPaths = pathHistory.map((path, index) => {
            // Convert to SVG path format
            const svgPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            
            // Get path data string (d attribute) with physical coordinates
            const pathData = path.segments.map((segment, i) => {
                const x = segment.point.x * scaleX;
                const y = segment.point.y * scaleY;
                return i === 0 ? `M${x},${y}` : `L${x},${y}`;
            }).join(' ');
            
            svgPath.setAttribute('d', pathData);
            svgPath.setAttribute('fill', 'none');
            svgPath.setAttribute('stroke', 'black');
            svgPath.setAttribute('stroke-width', '0.5');
            svgPath.setAttribute('id', `path-${index}`);
            svg.appendChild(svgPath);
            
            return {
                id: `path-${index}`,
                d: pathData,
                order: index
            };
        });
        
        // Create export data with SVG content
        const exportData = {
            svg: svgContainer.innerHTML,
            paths: svgPaths,
            drawingSequence: pathHistory.map((_, index) => `path-${index}`),
            canvasWidth: CANVAS_PHYSICAL_WIDTH,
            canvasHeight: CANVAS_PHYSICAL_HEIGHT
        };
        
        // This would be replaced with actual server upload code
        alert('Server upload functionality will be implemented later.');
        console.log('SVG data to upload:', exportData);
        
        // Example of how the upload might work with fetch API:
        /*
        fetch('https://your-server.com/api/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportData)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
            alert('Drawing uploaded successfully!');
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error uploading drawing. Please try again.');
        });
        */
    }
    
    // Event listeners for buttons
    document.getElementById('undo-btn').addEventListener('click', undoLastPath);
    document.getElementById('clear-btn').addEventListener('click', clearAll);
    document.getElementById('save-btn').addEventListener('click', saveDrawing);
    document.getElementById('upload-btn').addEventListener('click', uploadDrawing);
    
    // Initialize button states
    updateButtonStates();
    
    // Resize handler to maintain canvas size ratio
    paper.view.onResize = function() {
        // Maintain the 10:4 aspect ratio
        const containerWidth = document.querySelector('.canvas-container').offsetWidth;
        const containerHeight = containerWidth * (CANVAS_PHYSICAL_HEIGHT / CANVAS_PHYSICAL_WIDTH);
        
        paper.view.viewSize = new paper.Size(containerWidth, containerHeight);
    };
    
    // Initial update
    paper.view.update();
});