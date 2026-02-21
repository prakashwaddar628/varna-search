# Varna-Search Pro
**A lightning-fast, offline-first visual search engine built for professional design studios.**

Varna-Search Pro scans your massive local asset libraries, generating visual embeddings using an offline AI model. It allows high-volume production teams to instantly search for "concepts" or "colors" instead of relying on filenames, keeping users inside their existing OS environment.

## Key Features
*   **Vector Search Engine:** Find images based on what they *look* like, not what they're named. Find "a cyberpunk neon street" instantly.
*   **Offline First Model Inference**: Runs completely localized using the `.onnx` version of the sentence-transformers CLIP model, ensuring complete IP protection.
*   **Background Processing Isolate:** Never hangs the UI, even when crunching tens of thousands of TIFs, PSDs, and JPGs.
*   **Lightning Lookup:** Uses `ObjectBox` for high-performance localized memory storage of image vectors and file metadata.
*   **Native App Integration:** Uses `fluent_ui` to perfectly blend into Windows 11. Includes 1-click "Reveal in Explorer" buttons to easily drag-and-drop assets right into Photoshop or Illustrator.

## Monetization Model
*   **Trial Tier:** 100 Image limit.
*   **Monthly & Yearly:** Cloud-authenticated recurring subscriptions (powered by Supabase).
*   **Lifetime:** One-time purchase authentication.
*   Offline usage is heavily supported through a secure 3-day Grace Period system.

## Setup Instructions
1.  Ensure you have the Flutter SDK configured for **Windows Desktop** Development (`flutter config --enable-windows-desktop`).
2.  Run `flutter pub get`.
3.  Because `ObjectBox` requires generated bindings for Dart:
    ```bash
    dart run build_runner build --delete-conflicting-outputs
    ```
4.  Place your converted CLIP ONNX model at `assets/models/clip_model.onnx`. (Use our Python export script).
5.  Run: `flutter run -d windows`

## Architecture Highlights
*   **`ImageProcessor` Isolate:** Located at `/lib/features/processor/image_processor.dart`. Used to thread off heavy I/O and Onnx inference.
*   **`LicenseGuard`:** Located at `/lib/core/license/license_manager.dart`. Manages Supabase remote assertions alongside local `flutter_secure_storage` cached validations.
*   **State Management:** `flutter_riverpod` manages the complex asynchronous states of indexing folders and conducting nearest-neighbor Vector lookups.
