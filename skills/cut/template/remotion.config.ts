import {Config} from '@remotion/cli/config';

// The zone is rendered as h264 and then laid over the cut with ffmpeg, so
// overwriting the previous render is the normal case, not an accident.
Config.setOverwriteOutput(true);
Config.setVideoImageFormat('jpeg');
