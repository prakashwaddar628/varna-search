import 'package:flutter/foundation.dart';
import 'package:fluent_ui/fluent_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// import 'package:varna_search/core/license/license_manager.dart';
import 'features/search/presentation/varna_search_ui.dart';
import 'dart:io';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Example initialize license guard
  // final licenseGuard = LicenseGuard();
  // await licenseGuard.initialize();

  runApp(
    const ProviderScope(
      child: VarnaApp(),
    ),
  );
}

class VarnaApp extends StatelessWidget {
  const VarnaApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return FluentApp(
      title: 'Varna-Search Pro',
      themeMode: ThemeMode.dark,
      darkTheme: FluentThemeData(
        brightness: Brightness.dark,
        accentColor: Colors.blue,
        scaffoldBackgroundColor: const Color(0xFF1E1E1E), // Adobe dark
      ),
      home: const VarnaSearchPage(),
    );
  }
}
