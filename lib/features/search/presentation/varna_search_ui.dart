import 'dart:io';
import 'package:fluent_ui/fluent_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

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
}

// Mock Riverpod state provider
final searchResultsProvider = StateProvider<List<SearchResult>>((ref) {
  return [
    const SearchResult(path: 'C:\\DesignAssets\\NeonTiger.png', filename: 'NeonTiger.png', matchPercentage: 0.98),
    const SearchResult(path: 'C:\\DesignAssets\\CyberPunkCity.jpg', filename: 'CyberPunkCity.jpg', matchPercentage: 0.92),
    const SearchResult(path: 'C:\\DesignAssets\\AbstractWaves.png', filename: 'AbstractWaves.png', matchPercentage: 0.85),
    const SearchResult(path: 'C:\\DesignAssets\\LogoDraft.png', filename: 'LogoDraft.png', matchPercentage: 0.74),
  ];
});

final isSearchingProvider = StateProvider<bool>((ref) => false);

class VarnaSearchPage extends ConsumerStatefulWidget {
  const VarnaSearchPage({Key? key}) : super(key: key);

  @override
  ConsumerState<VarnaSearchPage> createState() => _VarnaSearchPageState();
}

class _VarnaSearchPageState extends ConsumerState<VarnaSearchPage> {
  final TextEditingController _searchController = TextEditingController();

  /// Reveal file in native OS file explorer
  Future<void> _revealInExplorer(String path) async {
    if (Platform.isWindows) {
      // Use Process to select the exact file in Windows Explorer
      await Process.run('explorer.exe', ['/select,', path]);
    } else if (Platform.isMacOS) {
      await Process.run('open', ['-R', path]);
    } else {
      // Fallback opens the directory
      final dir = File(path).parent.path;
      final uri = Uri.file(dir);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchResultsProvider);
    final isSearching = ref.watch(isSearchingProvider);

    return ScaffoldPage(
      header: PageHeader(
        title: const Text('Varna-Search Pro', style: TextStyle(fontWeight: FontWeight.bold)),
        commandBar: Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            SizedBox(
              width: 300,
              child: TextBox(
                controller: _searchController,
                placeholder: 'Search visual concepts (e.g. "red neon city")...',
                prefix: const Padding(
                  padding: EdgeInsets.only(left: 8.0),
                  child: Icon(FluentIcons.search),
                ),
                suffixMode: OverlayVisibilityMode.editing,
                suffix: IconButton(
                  icon: const Icon(FluentIcons.clear),
                  onPressed: () => _searchController.clear(),
                ),
                onSubmitted: (value) {
                  // Trigger vector search provider update
                  ref.read(isSearchingProvider.notifier).state = true;
                  // Handle vector lookup logic here...
                  Future.delayed(const Duration(milliseconds: 800), () {
                    ref.read(isSearchingProvider.notifier).state = false;
                  });
                },
              ),
            ),
            const SizedBox(width: 16),
            Button(
              child: const Row(
                children: [
                  Icon(FluentIcons.add),
                  SizedBox(width: 8),
                  Text('Index Folder'),
                ],
              ),
              onPressed: () {
                // Implement folder picker and trigger ImageProcessor isolate...
              },
            ),
          ],
        ),
      ),
      content: isSearching
          ? const Center(child: ProgressRing())
          : Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 8.0),
              child: GridView.builder(
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 220,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 0.85,
                ),
                itemCount: results.length,
                itemBuilder: (context, index) {
                  final item = results[index];
                  return _buildResultCard(item);
                },
              ),
            ),
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
                    color: theme.resources.layerOnMicaBaseAltFillColorDefault,
                    child: Center(
                      child: Icon(FluentIcons.photo_collection, size: 48, color: theme.inactiveColor),
                      // Uncomment to use actual file images:
                      // child: Image.file(File(item.path), fit: BoxFit.cover, errorBuilder: (_, __, ___) => Icon(FluentIcons.error)),
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
                        Text(
                          '${(item.matchPercentage * 100).toStringAsFixed(1)}% Match',
                          style: theme.typography.caption?.copyWith(
                            color: matchColor,
                            fontWeight: FontWeight.bold,
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
