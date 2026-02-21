import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:logger/logger.dart';

enum LicenseType { trial, monthly, yearly, lifetime }

class LicenseState {
  final LicenseType type;
  final bool isValid;
  final int trialImagesIndexed;
  final DateTime? lastOnlineCheck;

  const LicenseState({
    required this.type,
    required this.isValid,
    required this.trialImagesIndexed,
    this.lastOnlineCheck,
  });

  bool get canIndex => isValid || (type == LicenseType.trial && trialImagesIndexed < 100);
}

class LicenseGuard {
  static const String _licenseKeyToken = 'varna_license_key';
  static const String _licenseDataToken = 'varna_license_data';
  static const int _gracePeriodDays = 3;

  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final SupabaseClient _supabase = Supabase.instance.client;
  final Logger _logger = Logger();

  LicenseState _currentState = const LicenseState(
    type: LicenseType.trial,
    isValid: true,
    trialImagesIndexed: 0,
  );

  LicenseState get state => _currentState;

  /// Initializes the LicenseGuard, checks local encrypted storage and sets state.
  Future<void> initialize() async {
    final licenseDataStr = await _secureStorage.read(key: _licenseDataToken);
    
    if (licenseDataStr == null) {
      _logger.i('No license found. Starting in Trial mode.');
      return; // Uses default trial state
    }

    try {
      final Map<String, dynamic> data = jsonDecode(licenseDataStr);
      final type = LicenseType.values.firstWhere((e) => e.name == data['type']);
      final lastCheckStr = data['lastCheck'];
      final lastCheck = lastCheckStr != null ? DateTime.parse(lastCheckStr) : null;
      
      bool isValidLocal = _validateLocal(type, lastCheck, data['expiryDate']);

      _currentState = LicenseState(
        type: type,
        isValid: isValidLocal,
        trialImagesIndexed: data['trialIndexed'] ?? 0,
        lastOnlineCheck: lastCheck,
      );

      // Perform a background heartbeat check if possible
      if (isValidLocal && type != LicenseType.lifetime) {
        _heartbeatCheck(licenseDataStr);
      }
    } catch (e) {
      _logger.e('Failed to parse local license data. Reverting to Trial.', error: e);
    }
  }

  /// Checks if the local license is still within the grace period or lifetime.
  bool _validateLocal(LicenseType type, DateTime? lastCheck, String? expiryStr) {
    if (type == LicenseType.lifetime) return true;
    
    if (expiryStr != null) {
      final expiry = DateTime.parse(expiryStr);
      if (DateTime.now().isAfter(expiry)) return false;
    }

    if (lastCheck != null) {
      final daysOffline = DateTime.now().difference(lastCheck).inDays;
      if (daysOffline > _gracePeriodDays) {
        _logger.w('License grace period expired ($daysOffline days offline). Heartbeat required.');
        return false;
      }
    }
    
    return true;
  }

  /// Validates the license against the Supabase backend.
  Future<void> _heartbeatCheck(String licenseKey) async {
    try {
      final response = await _supabase.rpc('validate_license', params: {'key': licenseKey});
      
      if (response['is_valid'] == true) {
        final newType = LicenseType.values.firstWhere((e) => e.name == response['type']);
        await _saveLicenseLocally(
          type: newType,
          expiryDate: response['expiry_date'],
        );
        _logger.i('Heartbeat check successful. License updated.');
      } else {
        _logger.w('Heartbeat check failed: License revoked or expired on server.');
        await _invalidateLicenseLocally();
      }
    } catch (e) {
      _logger.w('Offline or unable to reach server. Using local grace period.', error: e);
    }
  }

  /// Called when a user activates a new license key.
  Future<bool> activateLicense(String key) async {
    try {
      final response = await _supabase.rpc('activate_license', params: {'key': key});
      
      if (response['success'] == true) {
        final newType = LicenseType.values.firstWhere((e) => e.name == response['type']);
        await _saveLicenseLocally(
          type: newType,
          expiryDate: response['expiry_date'],
          key: key,
        );
        _logger.i('License activated successfully: ${newType.name}');
        return true;
      }
      return false;
    } catch (e) {
      _logger.e('Activation failed', error: e);
      return false;
    }
  }

  Future<void> _saveLicenseLocally({
    required LicenseType type, 
    String? expiryDate, 
    String? key,
  }) async {
    final currentDict = jsonDecode(await _secureStorage.read(key: _licenseDataToken) ?? '{}');
    
    final newData = {
      'type': type.name,
      'lastCheck': DateTime.now().toIso8601String(),
      'expiryDate': expiryDate,
      'trialIndexed': currentDict['trialIndexed'] ?? 0,
    };

    await _secureStorage.write(key: _licenseDataToken, value: jsonEncode(newData));
    if (key != null) {
      await _secureStorage.write(key: _licenseKeyToken, value: key);
    }

    _currentState = LicenseState(
      type: type,
      isValid: true,
      trialImagesIndexed: newData['trialIndexed'],
      lastOnlineCheck: DateTime.now(),
    );
  }

  Future<void> _invalidateLicenseLocally() async {
    await _secureStorage.delete(key: _licenseDataToken);
    await _secureStorage.delete(key: _licenseKeyToken);
    _currentState = const LicenseState(type: LicenseType.trial, isValid: false, trialImagesIndexed: 0);
  }

  /// Increments the indexed image count for the trial tier.
  Future<void> incrementTrialIndexCount() async {
    if (_currentState.type != LicenseType.trial) return;

    final currentCount = _currentState.trialImagesIndexed + 1;
    final currentDictStr = await _secureStorage.read(key: _licenseDataToken) ?? '{}';
    Map<String, dynamic> data = currentDictStr.isNotEmpty ? jsonDecode(currentDictStr) : {};
    
    data['type'] = LicenseType.trial.name;
    data['trialIndexed'] = currentCount;
    
    await _secureStorage.write(key: _licenseDataToken, value: jsonEncode(data));
    
    _currentState = LicenseState(
      type: LicenseType.trial,
      isValid: _currentState.isValid,
      trialImagesIndexed: currentCount,
      lastOnlineCheck: _currentState.lastOnlineCheck,
    );
  }
}
