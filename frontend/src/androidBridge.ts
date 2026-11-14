// Compatibility exports for existing Android integrations.
export {takeNativePhoto as takeAndroidPhoto, scanNativeQr as scanAndroidQr} from './nativeBridge';
export function isAndroidApp() { return Boolean(window.GivingFlowAndroid); }
