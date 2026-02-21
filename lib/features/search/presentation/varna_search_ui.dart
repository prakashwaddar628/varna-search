import 'dart:io';
import 'dart:ui';
import 'package:fluent_ui/fluent_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:desktop_drop/desktop_drop.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;

// Mock model for UI demonstration
class SearchResult {
  final String path;
  final String filename;
  final double matchPercentage;

  const SearchResult({
    required this.path,
    required this.filename,
    required this.matchPercentage,
  });

  factory SearchResult.fromJson(Map<String, dynamic> json) {
    return SearchResult(
      path: json['path'],
      filename: json['filename'],
      matchPercentage: json['score'].toDouble(),
    );
  }
}

// --- Riverpod State Providers ---

// The folder currently selected to be indexed
final indexedFolderPathProvider = StateProvider<String?>((ref) => null);

// Is the system actively mocking an index scan?
final isIndexingProvider = StateProvider<bool>((ref) => false);

// The selected image we want to search for
final selectedImageQueryProvider = StateProvider<String?>((ref) => null);

// Is the system pulling vector distances?
final isSearchingProvider = StateProvider<bool>((ref) => false);

// The user-defined limit of results to return (e.g. top 10)
final matchLimitProvider = StateProvider<int>((ref) => 10);

// Are we currently dragging a file over the window?
final isDraggingProvider = StateProvider<bool>((ref) => false);

// The mock results returned from the database
final searchResultsProvider = StateProvider<List<SearchResult>>((ref) => []);

class VarnaSearchPage extends ConsumerStatefulWidget {
  const VarnaSearchPage({Key? key}) : super(key: key);

  @override
  ConsumerState<VarnaSearchPage> createState() => _VarnaSearchPageState();
}

class _VarnaSearchPageState extends ConsumerState<VarnaSearchPage> {

  /// Reveal file in native OS file explorer
  Future<void> _revealInExplorer(String path) async {
    if (Platform.isWindows) {
      await Process.run('explorer.exe', ['/select,', path]);
    } else if (Platform.isMacOS) {
      await Process.run('open', ['-R', path]);
    } else {
      final dir = File(path).parent.path;
      final uri = Uri.file(dir);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    }
  }

  /// 1. Prompts the user to pick a folder to index.
  Future<void> _pickFolderToIndex() async {
    final String? directoryPath = await getDirectoryPath(
      confirmButtonText: 'Select Folder to Index',
    );
    
    if (directoryPath != null) {
      ref.read(indexedFolderPathProvider.notifier).state = directoryPath;
      ref.read(isIndexingProvider.notifier).state = true;
      ref.read(searchResultsProvider.notifier).state = []; // Clear old results
      
      try {
        final uri = Uri.parse('http://127.0.0.1:8000/index_folder');
        final response = await http.post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({"folder_path": directoryPath}),
        );
        
        if (mounted) {
          ref.read(isIndexingProvider.notifier).state = false;
          if (response.statusCode == 200) {
            final data = jsonDecode(response.body);
            _showInfoBar('Indexing Complete', 'Extracted CLIP vectors for \${data["count"]} images in \${directoryPath}');
          } else {
             _showInfoBar('Indexing Failed', 'Backend returned \${response.statusCode}: \${response.body}', InfoBarSeverity.error);
          }
        }
      } catch (e) {
        if (mounted) {
          ref.read(isIndexingProvider.notifier).state = false;
          _showInfoBar('Connection Error', 'Could not reach Python backend. Make sure uvicorn is running. \n\n\$e', InfoBarSeverity.error);
        }
      }
    }
  }

  /// 2. Prompts the user to pick an image to search visually.
  Future<void> _pickImageToSearch() async {
    final String? folder = ref.read(indexedFolderPathProvider);
    if (folder == null) {
      _showInfoBar('No Folder Indexed', 'Please index a directory before searching.', InfoBarSeverity.warning);
      return;
    }

    const typeGroup = XTypeGroup(
      label: 'images',
      extensions: ['jpg', 'jpeg', 'png', 'webp', 'tif', 'tiff'],
    );
    final file = await openFile(acceptedTypeGroups: [typeGroup]);
    if (file != null) {
      _processImageSearch(file.path);
    }
  }

  /// Triggered either via file picker or drag-and-drop
  void _processImageSearch(String path) {
    final String? folder = ref.read(indexedFolderPathProvider);
    if (folder == null) {
      _showInfoBar('No Folder Indexed', 'Please index a directory before searching.', InfoBarSeverity.warning);
      return;
    }

    ref.read(selectedImageQueryProvider.notifier).state = path;
    ref.read(isSearchingProvider.notifier).state = true;
    
    // Send HTTP POST to FastAPI backend for CLIP search
    final limit = ref.read(matchLimitProvider);
    
    () async {
      try {
        final uri = Uri.parse('http://127.0.0.1:8000/search_image');
        var request = http.MultipartRequest('POST', uri);
        request.fields['limit'] = limit.toString();
        request.files.add(await http.MultipartFile.fromPath('file', path));
        
        final streamedResponse = await request.send();
        final response = await http.Response.fromStream(streamedResponse);
        
        if (!mounted) return;
        ref.read(isSearchingProvider.notifier).state = false;
        
        if (response.statusCode == 200) {
          final List<dynamic> data = jsonDecode(response.body);
          final List<SearchResult> results = data.map((json) => SearchResult.fromJson(json)).toList();
          
          if (results.isEmpty) {
            _showInfoBar('No Matches', 'No similar images found in the indexed folder.', InfoBarSeverity.info);
          }
          
          ref.read(searchResultsProvider.notifier).state = results;
        } else {
          _showInfoBar('Search Failed', 'Backend returned \${response.statusCode}: \${response.body}', InfoBarSeverity.error);
        }
      } catch (e) {
        if (!mounted) return;
        ref.read(isSearchingProvider.notifier).state = false;
        _showInfoBar('Connection Error', 'Could not reach Python backend to process image.\n\n\$e', InfoBarSeverity.error);
      }
    }();
  }

  void _showInfoBar(String title, String message, [InfoBarSeverity severity = InfoBarSeverity.success]) {
    displayInfoBar(
      context,
      builder: (context, close) {
        return InfoBar(
          title: Text(title),
          content: Text(message),
          action: IconButton(
            icon: const Icon(FluentIcons.clear),
            onPressed: close,
          ),
          severity: severity,
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDragging = ref.watch(isDraggingProvider);
    final isIndexing = ref.watch(isIndexingProvider);
    final indexedFolder = ref.watch(indexedFolderPathProvider);
    final results = ref.watch(searchResultsProvider);

    return DropTarget(
      onDragDone: (detail) {
        if (detail.files.isNotEmpty) {
          final file = detail.files.first;
          // Basic extension check
          final ext = file.path.split('.').last.toLowerCase();
          if (['png', 'jpg', 'jpeg', 'webp', 'tif', 'tiff'].contains(ext)) {
            _processImageSearch(file.path);
          } else {
             _showInfoBar('Invalid File', 'Please drop a valid image file to search.', InfoBarSeverity.error);
          }
        }
      },
      onDragEntered: (detail) => ref.read(isDraggingProvider.notifier).state = true,
      onDragExited: (detail) => ref.read(isDraggingProvider.notifier).state = false,
      child: ScaffoldPage(
        header: PageHeader(
          title: const Text('Varna-Search Pro', style: TextStyle(fontWeight: FontWeight.bold)),
          commandBar: indexedFolder != null 
              ? Text('📍 Indexed: \$indexedFolder', style: TextStyle(color: FluentTheme.of(context).typography.caption?.color ?? Colors.grey))
              : null,
        ),
        content: Stack(
          children: [
            Column(
              children: [
                // --- Dashboard Hero Area ---
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Action 1: Index Folder Card
                      Expanded(
                        child: _buildActionCard(
                          title: '1. Index a Folder',
                          subtitle: indexedFolder == null 
                                    ? 'Select a local drive or folder to scan.' 
                                    : 'Ready. Click to re-index.',
                          icon: FluentIcons.folder_open,
                          isLoading: isIndexing,
                          onTap: isIndexing ? null : _pickFolderToIndex,
                          isHighlight: indexedFolder == null,
                        ),
                      ),
                      const SizedBox(width: 24),
                      // Action 2: Search by Image Card
                      Expanded(
                        child: _buildActionCard(
                          title: '2. Visually Search',
                          subtitle: 'Upload or drop a reference image here.',
                          icon: FluentIcons.image_search,
                          isLoading: ref.watch(isSearchingProvider),
                          onTap: indexedFolder == null || isIndexing ? null : _pickImageToSearch,
                          isHighlight: indexedFolder != null,
                        ),
                      ),
                    ],
                  ),
                ),

                // --- Match Limit Configuration ---
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 8.0),
                  child: Row(
                    children: [
                      const Icon(FluentIcons.slider),
                      const SizedBox(width: 12),
                      Flexible(
                        child: const Text('Result Display Limit:', style: TextStyle(fontWeight: FontWeight.w600), overflow: TextOverflow.ellipsis,),
                      ),
                      const SizedBox(width: 24),
                      Expanded(
                        flex: 3,
                        child: Slider(
                          min: 1.0,
                          max: 10.0,
                          value: ref.watch(matchLimitProvider).toDouble(),
                          label: 'Top \${ref.watch(matchLimitProvider)} Images',
                          onChanged: (v) => ref.read(matchLimitProvider.notifier).state = v.toInt(),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Flexible(
                        child: Text('Top \${ref.watch(matchLimitProvider)}', 
                             style: TextStyle(fontWeight: FontWeight.bold, color: FluentTheme.of(context).accentColor), overflow: TextOverflow.ellipsis,),
                      ),
                    ],
                  ),
                ),
                
                const Divider(),

                // --- Results Area ---
                Expanded(
                  child: results.isEmpty 
                    ? _buildEmptyState() 
                    : Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (ref.watch(selectedImageQueryProvider) != null)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 16.0),
                                child: Row(
                                  children: [
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(8.0),
                                      child: Image.file(
                                        File(ref.watch(selectedImageQueryProvider)!),
                                        width: 64,
                                        height: 64,
                                        fit: BoxFit.cover,
                                      ),
                                    ),
                                    const SizedBox(width: 16),
                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Search Results', style: FluentTheme.of(context).typography.subtitle),
                                        Text('Showing top \${results.length} visually similar images', 
                                            style: TextStyle(color: FluentTheme.of(context).typography.caption?.color)),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            Expanded(
                              child: GridView.builder(
                                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 240,
                                  crossAxisSpacing: 16,
                                  mainAxisSpacing: 16,
                                  childAspectRatio: 0.85,
                                ),
                                itemCount: results.length,
                                itemBuilder: (context, index) {
                                  return _buildResultCard(results[index]);
                                },
                              ),
                            ),
                          ],
                        ),
                      ),
                ),
              ],
            ),

            // Base Drag-and-drop Visual Overlay
            if (isDragging)
              Positioned.fill(
                child: Container(
                  color: FluentTheme.of(context).accentColor.withOpacity(0.15),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 5.0, sigmaY: 5.0),
                    child: Center(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 40.0),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(FluentIcons.cloud_download, 
                                   size: 80, 
                                   color: FluentTheme.of(context).accentColor),
                              const SizedBox(height: 16),
                              const Text(
                                'Drop image to visually search indexed folder',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                        ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    final indexedFolder = ref.read(indexedFolderPathProvider);
    final isSearching = ref.read(isSearchingProvider);
    final isIndexing = ref.read(isIndexingProvider);

    if (isIndexing) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: const [
            ProgressRing(),
            SizedBox(height: 16),
            Text('Scanning directories and generating vectors...', style: TextStyle(color: Colors.grey)),
          ],
        )
      );
    }

    if (isSearching) {
      return const Center(child: ProgressRing());
    }

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(FluentIcons.search_and_apps, size: 64, color: FluentTheme.of(context).typography.caption?.color ?? Colors.grey),
          const SizedBox(height: 16),
          Text(
            indexedFolder == null 
              ? 'Start by indexing a folder.' 
              : 'Folder indexed! Drop or select an image to find similar designs.',
            style: TextStyle(color: FluentTheme.of(context).typography.caption?.color ?? Colors.grey, fontSize: 16),
          ),
        ],
      ),
    );
  }

  Widget _buildActionCard({
    required String title, 
    required String subtitle, 
    required IconData icon, 
    required bool isLoading,
    required VoidCallback? onTap,
    required bool isHighlight,
  }) {
    final theme = FluentTheme.of(context);
    final bool disabled = onTap == null;

    return HoverButton(
      onPressed: onTap,
      builder: (context, states) {
        final isHovered = states.isHovered && !disabled;
        
        return AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(24.0),
          decoration: BoxDecoration(
            color: isHighlight ? theme.accentColor.withValues(alpha: 0.1) : theme.cardColor,
            borderRadius: BorderRadius.circular(12.0),
            border: Border.all(
              color: isHovered 
                  ? theme.accentColor 
                  : (isHighlight ? theme.accentColor.withValues(alpha: 0.5) : theme.resources.dividerStrokeColorDefault),
              width: isHovered ? 2.0 : 1.5,
            ),
            boxShadow: isHovered
                ? [BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 8, offset: const Offset(0, 4))]
                : [],
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(16.0),
                decoration: BoxDecoration(
                  color: isHighlight ? theme.accentColor : theme.resources.dividerStrokeColorDefault,
                  shape: BoxShape.circle,
                ),
                child: isLoading 
                    ? const ProgressRing() 
                    : Icon(icon, size: 32, color: isHighlight ? Colors.white : theme.resources.textOnAccentFillColorPrimary),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title, 
                      style: TextStyle(
                        fontSize: 20, 
                        fontWeight: FontWeight.bold,
                        color: disabled ? theme.typography.caption?.color : theme.typography.bodyStrong!.color,
                      )
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle, 
                      style: TextStyle(color: disabled ? theme.typography.caption?.color : theme.typography.caption!.color)
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      }
    );
  }

  Widget _buildResultCard(SearchResult item) {
    final theme = FluentTheme.of(context);
    
    // Determine Adobe-like match color
    Color matchColor = item.matchPercentage > 0.90
        ? Colors.green
        : (item.matchPercentage > 0.70 ? Colors.orange : theme.typography.caption!.color!);

    return HoverButton(
      onPressed: () {},
      builder: (context, states) {
        final isHovered = states.isHovered;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: theme.cardColor,
            borderRadius: BorderRadius.circular(8.0),
            border: Border.all(
              color: isHovered ? theme.accentColor : theme.resources.dividerStrokeColorDefault,
              width: 1.5,
            ),
            boxShadow: isHovered
                ? [BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 10, offset: const Offset(0, 4))]
                : [],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Image Thumbnail Area
              Expanded(
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(6.0)),
                  child: Container(
                    width: double.infinity,
                    color: theme.resources.layerOnMicaBaseAltFillColorDefault,
                    child: FittedBox(
                      fit: BoxFit.cover,
                      clipBehavior: Clip.hardEdge,
                      child: Image.file(
                        File(item.path), 
                        errorBuilder: (_, __, ___) => Padding(
                          padding: const EdgeInsets.all(24.0),
                          child: Icon(FluentIcons.photo_collection, size: 48, color: theme.inactiveColor),
                        )
                      ),
                    ),
                  ),
                ),
              ),
              // Metadata & Actions
              Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.filename,
                      style: theme.typography.bodyStrong,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Flexible(
                          child: Text(
                            '\${(item.matchPercentage * 100).toStringAsFixed(1)}% Match',
                            style: theme.typography.caption?.copyWith(
                              color: matchColor,
                              fontWeight: FontWeight.bold,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Tooltip(
                          message: 'Show in Explorer',
                          child: IconButton(
                            icon: const Icon(FluentIcons.folder_open),
                            onPressed: () => _revealInExplorer(item.path),
                            style: ButtonStyle(
                              padding: WidgetStateProperty.all(const EdgeInsets.all(4)),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
