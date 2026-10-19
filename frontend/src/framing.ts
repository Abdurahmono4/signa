export const INTERPRETER_FOV=24;
export const INTERPRETER_TARGET_Y=1.49;

// Conservative support points in metres, verified across the captured corpus.
// They include 5 cm around every hand/finger joint. The camera stays stable
// between signs and changes only when the viewport or viewing angle changes.
const horizontalSupport=[ [.35,.75],[.45,.70],[.55,.65],[.60,.55],[.65,.50],[.70,.45] ];
const halfFov=Math.tan(INTERPRETER_FOV*Math.PI/360);
export function interpreterCameraDistance(aspect:number,angle=0){
 const ratio=Number.isFinite(aspect)&&aspect>0?aspect:1;
 const rotation=Number.isFinite(angle)?angle:0;
 const cosine=Math.abs(Math.cos(rotation)),sine=Math.abs(Math.sin(rotation));
 // 13% vertical and 10% horizontal padding keep the face and fingertips clear.
 const vertical=3.5+.7*sine;
 const horizontal=Math.max(...horizontalSupport.map(([x,z])=>{
  const width=x*cosine+z*sine,front=x*sine+z*cosine;
  return front+width/(halfFov*ratio*.90);
 }));
 return Math.max(vertical,horizontal);
}

export type SigningEnvelope={min:[number,number,number];max:[number,number,number]};
// The studio opens on the interpreter's face and hands before a generated
// sequence has supplied its exact envelope. Do not use the corpus-wide camera
// here: portrait panels would include the legs until the first sign loads.
const REST_SIGNING_ENVELOPE:SigningEnvelope={min:[-.28,1.04,-.08],max:[.28,2.01,.15]};
export function studioInterpreterCamera(aspect:number,angle=0){
 const framing=neuralInterpreterCamera(REST_SIGNING_ENVELOPE,aspect,angle);
 // Keep the lower edge at the waist even in a narrow studio panel.
 return {...framing,targetY:Math.max(framing.targetY,1.07+halfFov*framing.distance)};
}
export function neuralInterpreterCamera(envelope:SigningEnvelope,aspect:number,angle=0){
 if(!envelope||!Array.isArray(envelope.min)||!Array.isArray(envelope.max)||envelope.min.length!==3||envelope.max.length!==3||
  [...envelope.min,...envelope.max].some(value=>!Number.isFinite(value)||Math.abs(value)>20)||envelope.min.some((value,index)=>value>envelope.max[index])||
  envelope.max.every((value,index)=>value-envelope.min[index]<1e-6))throw new Error('Invalid neural signing envelope.');
 const ratio=Number.isFinite(aspect)&&aspect>0?aspect:1,rotation=Number.isFinite(angle)?angle:0;
 const cosine=Math.cos(rotation),sine=Math.sin(rotation),points:number[][]=[];
 for(const x of [envelope.min[0],envelope.max[0]])for(const y of [envelope.min[1],envelope.max[1]])for(const z of [envelope.min[2],envelope.max[2]])points.push([x*cosine+z*sine,y,-x*sine+z*cosine]);
 const x=(Math.min(...points.map(point=>point[0]))+Math.max(...points.map(point=>point[0])))/2;
 const targetY=(envelope.min[1]+envelope.max[1])/2;
 // Keep a stable 12% surface margin. The envelope covers the entire prepared
 // sequence, so recorded movement cannot produce per-frame camera zooming.
 const distance=Math.max(.75,...points.flatMap(point=>[
  point[2]+Math.abs(point[0]-x)/(halfFov*ratio*.88),
  point[2]+Math.abs(point[1]-targetY)/(halfFov*.88),point[2]+.2,
 ]));
 return {x,targetY,distance};
}
