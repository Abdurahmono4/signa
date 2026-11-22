import type {Camera} from 'three';

/** Common framing for the live canvas, MP4 and geometry checks. */
export function positionAvatarCamera(camera:Camera){
 camera.position.set(0,1.27,2.06);
 camera.lookAt(0,1.27,0);
 camera.updateMatrixWorld(true);
}
