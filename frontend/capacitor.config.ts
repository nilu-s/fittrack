import type { CapacitorConfig } from '@capacitor/cli';

const apiOrigin = process.env.CRONICL_API_ORIGIN ?? 'https://cronicl.49.12.225.84.sslip.io';
if (!/^https:\/\/[^/]+$/.test(apiOrigin)) throw new Error('CRONICL_API_ORIGIN must be an HTTPS origin without a path');

const config: CapacitorConfig = {
  appId: 'app.cronicl.mobile',
  appName: 'Cronicl',
  webDir: 'build-mobile',
  plugins: {
    CroniclNative: { apiOrigin },
    PushNotifications: { presentationOptions: ['badge', 'sound', 'alert'] },
  },
};
export default config;
