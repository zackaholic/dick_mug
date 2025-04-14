# Mug Plotter Drawing App

A web-based drawing application for a CNC plotter system that draws on coffee mugs.

## Features

- Fixed canvas representing a 60mm x 150mm physical surface area (standard mug wrap area)
- Single-color line drawing with mouse input
- Path smoothing for cleaner output and GCode generation
- Undo functionality and clear all option
- Save drawings as SVG files with complete path data
- Upload drawings to plotter server (to be implemented)

## Setup

1. Clone this repository
2. Open `index.html` in a modern web browser

## Usage

1. Draw on the canvas with your mouse
2. Use the Undo button to remove the last drawn path
3. Use Clear All to start over
4. Save Drawing will download both SVG and JSON files containing the path data
5. Upload to Plotter will send the drawing to the CNC plotter (coming soon)

## Technical Details

- Canvas dimensions: 60mm x 150mm (physical), 600px x 240px (screen)
- Uses Paper.js for path handling and smoothing
- Drawings are saved with physical coordinates in millimeters

## Future Plans

- Server-side component for GCode generation
- CNC plotter integration
- Multiple color support
- Varying line width
- Template shapes and guides
