import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';
import settings from './site.settings.json';
import {resolveConfig} from './setup/lib/runtime.cjs';
export default resolveConfig(settings).sidebar as SidebarsConfig;
