import 'package:camera/camera.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/errors.dart';
import '../../services/app_session.dart';
import '../common/status_screens.dart';
import 'verification_repository.dart';
import 'verification_service.dart';

class VerificationScreen extends StatefulWidget {
  const VerificationScreen({super.key});

  @override
  State<VerificationScreen> createState() => _VerificationScreenState();
}

class _VerificationScreenState extends State<VerificationScreen> with BusyState {
  final _repo = VerificationRepository();
  CameraController? _camera;
  bool _cameraUnavailable = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_camera == null &&
        !_cameraUnavailable &&
        VerificationScope.of(context).usesInAppCameraPreview) {
      _initCamera();
    }
  }

  /// Sadece canlı önizleme. takePicture() ÇAĞRILMAZ, hiçbir kare kaydedilmez.
  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      final front = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(front, ResolutionPreset.medium, enableAudio: false);
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() => _camera = controller);
    } catch (_) {
      if (mounted) setState(() => _cameraUnavailable = true);
    }
  }

  @override
  void dispose() {
    _camera?.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final session = SessionScope.of(context);
    final service = VerificationScope.of(context);
    final gender = session.state?.profile?.gender;
    if (gender == null) return;

    await runBusy(() async {
      final result = await service.verifySelfie(claimedGender: gender);
      if (!result.success) {
        if (result.errorMessage != null) showError(result.errorMessage!);
        return;
      }
      final ok = await _repo.confirm(providerToken: result.providerToken!, claimedGender: gender);
      if (!ok) {
        showError('Doğrulama başarısız oldu. Yüzünün net göründüğünden emin olup tekrar dene.');
        return;
      }
      await session.refresh();
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.watch(context);
    final profile = session.state?.profile;
    final theme = Theme.of(context);
    final reverify = profile?.needsReverification ?? false;

    return Scaffold(
      appBar: AppBar(title: Text(reverify ? 'Yeniden doğrulama' : 'Selfie doğrulama')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            if (reverify)
              Card(
                color: theme.colorScheme.errorContainer,
                child: const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    'Hakkında "cinsiyeti farklı" şikâyetleri geldi. '
                    'Sohbete devam edebilmek için tekrar selfie doğrulaması yapmalısın.',
                  ),
                ),
              ),
            Text(
              'Beyan ettiğin cinsiyet: ${profile?.gender?.label ?? '-'}',
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            AspectRatio(
              aspectRatio: 3 / 4,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: ColoredBox(
                  color: Colors.black12,
                  child: _camera != null && _camera!.value.isInitialized
                      ? CameraPreview(_camera!)
                      : Center(
                          child: Text(
                            _cameraUnavailable ? 'Kamera kullanılamıyor' : '📷',
                            style: const TextStyle(fontSize: 32),
                          ),
                        ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              '🔒 Fotoğrafın kaydedilmez ve saklanmaz. Sadece "doğrulandı" bilgisi tutulur.',
              style: theme.textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: busy ? null : _start,
              child: busy
                  ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator())
                  : const Text('Doğrulamayı başlat'),
            ),
            TextButton(
              onPressed: busy ? null : () => context.go('/gender'),
              child: const Text('Cinsiyet seçimini değiştir'),
            ),
          ],
        ),
      ),
    );
  }
}
