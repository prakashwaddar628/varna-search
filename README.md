# LAXPRA - AI Design Matcher

A powerful desktop application for finding similar designs using advanced computer vision. LAXPRA intelligently analyzes design images and matches them against a custom design vault, helping designers quickly discover similar patterns, textures, and styles.

## Features

✨ **Intelligent Design Matching**
- Uses SIFT (Scale-Invariant Feature Transform) for texture analysis
- Color histogram analysis for accurate color matching
- Memory-safe feature extraction to prevent crashes

🎨 **Multi-Format Support**
- PNG, JPG, JPEG images
- CDR (CorelDRAW) files with automatic preview extraction
- Drag-and-drop support for easy image handling

📊 **Visual Comparison**
- Clean, modern UI with Laxpra branding
- Similarity scores (0-100%) for each match
- Top 12 most similar designs displayed in grid layout
- Beautiful design cards with visual previews

🔧 **Easy Indexing**
- One-click folder indexing to build your design vault
- Recursive directory scanning with smart exclusions
- SQLite database for efficient feature storage
- Progress tracking during indexing

🎯 **Interactive Cropping**
- Select specific jersey/garment areas to focus matching
- Reduces background noise for more accurate results
- OpenCV-based ROI selection interface

## Installation

### Prerequisites
- Python 3.8+
- Windows, macOS, or Linux

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd varna-search
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
python main.py
```

The LAXPRA window will open with two main workflow steps.

### Workflow

#### Step 1: Index Your Design Folder
1. Click **"📁 Step 1: Index Design Folder"**
2. Select the folder containing your design assets
3. The application will scan all subdirectories for design images
4. Features will be extracted and stored in `design_vault.db`
5. Progress bar shows indexing status

#### Step 2: Search for Similar Designs

**Option A: Select & Crop**
1. Click **"🔍 Step 2: Select Photo & Crop"**
2. Choose an image from your computer
3. Use the OpenCV ROI selector to draw a box around the area you want to analyze
   - Drag to create a selection box
   - Press **ENTER** or **SPACE** to confirm
   - Press **'c'** to cancel
4. The application finds and displays the top 12 matching designs

**Option B: Drag & Drop**
1. Simply drag an image file into the LAXPRA window
2. Results will instantly appear

### Understanding Results

- **Match Score**: Displayed as a percentage (0-100%)
  - Green badge: >75% similarity (high confidence)
  - Orange badge: <75% similarity (moderate match)
- **Similarity Threshold**: Only designs with >30% similarity are shown
- **Design Cards**: Click any card to open it in your file explorer

## Project Structure

```
varna-search/
├── main.py              # PyQt6 GUI application
├── engine.py            # Computer vision engine (SIFT, histograms)
├── database.py          # SQLite design vault management
├── requirements.txt     # Python dependencies
├── design_vault.db      # Generated SQLite database
├── embedder.tflite      # (Optional) TensorFlow Lite models
└── README.md           # This file
```

## Dependencies

- **PyQt6**: Modern GUI framework with native look & feel
- **OpenCV**: Computer vision for image processing and SIFT
- **NumPy**: Numerical computing for feature vectors

See `requirements.txt` for specific versions.

## Technical Details

### Feature Extraction

The application extracts two types of features from each design:

1. **Texture Features (SIFT)**
   - Detects corner and edge points robust to rotation/scale
   - Limited to 1000 features per image to prevent memory issues
   - Provides rich texture information

2. **Color Features (Histogram)**
   - HSV color distribution analysis
   - 8x8x8 histogram bins for color space coverage
   - Normalized for consistent comparison

### Memory Safety

- Images are resized to max 600px width to prevent OutOfMemory errors
- Aspect ratio is preserved during resizing
- Memory is explicitly freed after feature extraction
- Suitable for processing large design libraries

### Matching Algorithm

- Compares SIFT keypoint descriptors between designs
- Calculates color histogram similarity
- Combined scoring for robust matching
- Filters results by confidence threshold

## Building Executables

This project includes a PyInstaller spec file (`Laxpra-AI-Matcher.spec`) for creating standalone executables:

```bash
pyinstaller Laxpra-AI-Matcher.spec
```

The resulting executable will be in the `dist/` folder.

## Troubleshooting

**"Extraction Error" messages**
- Ensure image files are valid and not corrupted
- Check that you have read permissions on the files
- CDR files must contain a `previews/preview.png` file

**No results found**
- Increase the similarity threshold in `main.py` (default: 0.3)
- Ensure you've indexed your design folder first
- Try searching with a cropped region for better results

**Slow indexing**
- Large folders may take time to index
- Excluded folders: AppData, Windows, .git, venv
- Consider indexing smaller batches initially

**Out of Memory**
- The engine automatically resizes large images
- If issues persist, reduce the folder size or split into batches

## Performance Tips

- Index designs in batches if you have 10,000+ files
- Use the cropping tool to focus on specific areas
- Adjust the similarity threshold (0.3-0.5) based on your needs
- Consider using images with consistent backgrounds

## Future Enhancements

- [ ] Neural network-based embeddings for improved accuracy
- [ ] GPU acceleration for faster processing
- [ ] Batch search across multiple images
- [ ] Custom similarity threshold settings UI
- [ ] Export matching results
- [ ] Undo/Redo for indexed searches

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or feature requests, please [add contact information or issue tracker link].

---

**LAXPRA** - The Perfect AI Matcher for your design vault.
