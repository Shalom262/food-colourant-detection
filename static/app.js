'use strict';
const $ = id => document.getElementById(id);
let selectedFile=null, objectUrl=null, result=null, task='powder', busy=false, modelReady=false;
const names={CurryPowder:'Curry powder',PillarRed:'Pillar red',RosePink:'Rose pink',LemonYellow:'Lemon yellow',EggYellow:'Egg yellow'};
const label=v=>names[v]||v;
function showError(message){$('errorMessage').textContent=message;$('errorMessage').hidden=!message;}
function syncButton(){$('analyzeButton').disabled=!selectedFile||!modelReady||busy;}
function chooseFile(file){
 if(busy)return;
 if(!file)return;
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)){showError('Please choose a JPG, PNG or WebP photo.');return;}
 if(file.size>15*1024*1024){showError('Please choose a photo under 15 MB.');return;}
 if(objectUrl)URL.revokeObjectURL(objectUrl);
 selectedFile=file;objectUrl=URL.createObjectURL(file);
 $('uploadPreview').src=objectUrl;$('uploadPreview').hidden=false;$('uploadPrompt').hidden=true;$('changeImage').hidden=false;
 $('fileDetails').hidden=false;$('fileName').textContent=file.name+' · '+(file.size/1024/1024).toFixed(2)+' MB';
 resetExplanations();result=null;$('resultState').hidden=true;$('emptyState').hidden=false;$('resultBadge').textContent='AWAITING ANALYSIS';
 showError('');syncButton();
}
$('dropZone').onclick=()=>{if(!busy)$('fileInput').click();};
$('fileInput').onchange=e=>chooseFile(e.target.files[0]);
['dragenter','dragover'].forEach(event=>$('dropZone').addEventListener(event,e=>{e.preventDefault();if(!busy)$('dropZone').classList.add('dragging');}));
['dragleave','drop'].forEach(event=>$('dropZone').addEventListener(event,e=>{e.preventDefault();$('dropZone').classList.remove('dragging');}));
$('dropZone').addEventListener('drop',e=>chooseFile(e.dataTransfer.files[0]));
$('clearFile').onclick=()=>{if(busy)return;selectedFile=null;resetExplanations();result=null;if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;$('fileInput').value='';$('uploadPreview').hidden=true;$('uploadPrompt').hidden=false;$('changeImage').hidden=true;$('fileDetails').hidden=true;$('resultState').hidden=true;$('emptyState').hidden=false;$('resultBadge').textContent='AWAITING SAMPLE';showError('');syncButton();};
const connectionMessage='The local server is disconnected. Open Start_SpiceScope.cmd in the SpiceScope_WebApp folder, then retry. Your photo has not been analyzed.';
function requestError(error){return error instanceof TypeError ? connectionMessage : error.message;}
async function health(){try{const response=await fetch('/api/health');if(!response.ok)throw Error();const data=await response.json();modelReady=data.status==='ready';$('modelStatus').className='status-chip '+data.status;$('statusText').textContent=modelReady?'DINOv3 ready · '+(data.device||'CPU').toUpperCase():data.status==='loading'?'Loading trained model…':'Model setup needed';$('modelStatus').title=data.message;if(data.status==='unavailable')showError(data.message);else if(modelReady&&$('errorMessage').textContent===connectionMessage)showError('');syncButton();return data.status;}catch{$('statusText').textContent='Backend disconnected';modelReady=false;$('modelStatus').className='status-chip unavailable';showError(connectionMessage);syncButton();return 'disconnected';}}
async function poll(){const status=await health();setTimeout(poll,status==='loading'?2500:5000);}
poll();
async function loadSamples(){try{const response=await fetch('/api/samples');if(!response.ok)throw Error();const data=await response.json();for(const sample of data){const button=document.createElement('button');button.className='sample';const image=document.createElement('img');image.src=sample.url;image.alt=sample.title+' dataset sample';const text=document.createElement('div');text.textContent=sample.title;const caption=document.createElement('span');caption.textContent='Try sample ↗';text.append(caption);button.append(image,text);button.onclick=async()=>{if(busy)return;try{const r=await fetch(sample.url);if(!r.ok)throw Error();chooseFile(new File([await r.blob()],sample.filename,{type:'image/jpeg'}));}catch{showError('Could not load this sample. Please upload your photo.');}};$('samples').append(button);}}catch{$('samples').textContent='Upload your own photo to begin.';}}
loadSamples();
function renderBars(){
 const probabilities=task==='powder'?result.raw_powder_probabilities:result.eligible_colouring_probabilities;
 const best=task==='powder'?result.powder:result.colouring;
 $('probabilityCaption').textContent=task==='powder'?'RAW MODEL PROBABILITIES':'ELIGIBLE CLASSES · RAW SCORES';
 $('scoreNote').textContent=task==='powder'?'Scores describe the model’s prediction. “Pure” is a dataset category, not a chemical purity measurement.':'Only powder-compatible classes are shown. Scores are unmodified model probabilities and may not sum to 100%; the full model output is in the JSON report.';
 $('probabilities').replaceChildren();
 for(const [key,value] of Object.entries(probabilities)){
 const row=document.createElement('div');row.className='probability'+(key===best?' best':'');
 const heading=document.createElement('div');heading.className='probability-heading';
 const name=document.createElement('span');name.textContent=label(key)+(key===best?' · predicted':'');
 const score=document.createElement('strong');score.textContent=(value*100).toFixed(2)+'%';heading.append(name,score);
 const track=document.createElement('div');track.className='bar';const fill=document.createElement('span');fill.style.width=(value*100)+'%';track.append(fill);row.append(heading,track);$('probabilities').append(row);
 }
}
function setTask(next){task=next;document.querySelectorAll('[data-task]').forEach(button=>{button.classList.toggle('active',button.dataset.task===task);button.setAttribute('aria-selected',String(button.dataset.task===task));});if(result)renderBars();}
document.querySelectorAll('[data-task]').forEach(button=>{button.onclick=()=>setTask(button.dataset.task);button.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();const other=document.querySelector('[data-task="'+(task==='powder'?'colouring':'powder')+'"]');other.click();other.focus();}};});
$('analyzeButton').onclick=async()=>{
 if(!selectedFile||busy||!modelReady)return;
 busy=true;resetExplanations();syncButton();showError('');$('emptyState').hidden=true;$('resultState').hidden=true;$('loadingState').hidden=false;$('resultBadge').textContent='ANALYZING';$('resultsPanel').setAttribute('aria-busy','true');$('analyzeLabel').textContent='Analyzing…';$('analyzeArrow').textContent='◎';
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),180000);const started=Date.now();
 const progress=setInterval(()=>{const seconds=Math.floor((Date.now()-started)/1000);$('loadingDetail').textContent=seconds<5?'Preparing powder region and colour features':seconds<15?'Reading visual patterns with DINOv3':'Still analyzing on your CPU · '+seconds+' seconds';},1500);
 try{const form=new FormData();form.append('file',selectedFile);const response=await fetch('/api/predict',{method:'POST',body:form,signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(data.detail||'Analysis failed. Please try again.');result=data;window.dispatchEvent(new CustomEvent('spicescope:prediction',{detail:{powder:data.powder}}));resetExplanations();$('explainSection').hidden=false;
 $('powderResult').textContent=label(data.powder);$('colourResult').textContent=label(data.colouring)+' · allowed for '+label(data.powder);
 const confidence=data.raw_powder_probabilities[data.powder];$('confidenceValue').textContent=(confidence*100).toFixed(1)+'%';$('confidenceRing').style.setProperty('--score',confidence*360+'deg');
 $('preparedPreview').src=data.prepared_preview;$('inferenceTime').textContent='Completed locally in '+data.elapsed_seconds.toFixed(2)+' s';$('resultBadge').textContent='ANALYSIS COMPLETE';setTask('powder');$('resultState').hidden=false;
 }catch(error){showError(error.name==='AbortError'?'This analysis took too long. Wait a moment before retrying on CPU.':requestError(error));$('emptyState').hidden=false;$('resultBadge').textContent='TRY ANOTHER PHOTO';}
 finally{clearTimeout(timeout);clearInterval(progress);busy=false;$('loadingState').hidden=true;$('resultsPanel').setAttribute('aria-busy','false');$('analyzeLabel').textContent='Analyze sample';$('analyzeArrow').textContent='↗';syncButton();}
};
$('downloadResult').onclick=()=>{if(!result)return;const report={...result};delete report.prepared_preview;if(report.explanations){const e=report.explanations;report.explanations={...e};delete report.explanations.prepared_image;report.explanations.cams=Object.fromEntries(Object.entries(e.cams).map(([k,v])=>{const item={...v};delete item.map;return [k,item];}));report.explanations.segmentation={coverage:e.segmentation.coverage,roi_valid:e.segmentation.roi_valid,note:e.segmentation.note};}report.exported_at=new Date().toISOString();const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='SpiceScope_'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('evidenceButton').onclick=async()=>{const content=$('evidenceContent');content.textContent='Loading exported test evidence…';$('evidenceDialog').showModal();try{const response=await fetch('/api/info');if(!response.ok)throw Error();const data=await response.json();const table=document.createElement('table');table.className='evidence-table';const header=document.createElement('tr');['Test unit','Powder accuracy','Colouring accuracy','Joint accuracy'].forEach(v=>{const th=document.createElement('th');th.textContent=v;header.append(th);});table.append(header);for(const row of data.test_evidence){const tr=document.createElement('tr');[row.unit==='video_id'?'Video (n='+row.n+')':'Frame (n='+row.n+')',...['powder_accuracy','colouring_accuracy','joint_accuracy'].map(k=>(Number(row[k])*100).toFixed(2)+'%')].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});table.append(tr);}content.replaceChildren(table);}catch{content.textContent='Test evidence is unavailable. Please reconnect to the local backend.';}};
$('closeEvidence').onclick=()=>$('evidenceDialog').close();$('evidenceDialog').addEventListener('click',e=>{if(e.target===$('evidenceDialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});


function resetExplanations(){
 window.dispatchEvent(new CustomEvent('spicescope:explanations-cleared'));
 $('explainSection').hidden=true;$('explainContent').hidden=true;$('explainProgress').hidden=true;$('explainError').hidden=true;$('explainButton').disabled=false;$('explainButton').innerHTML='Generate explanations <span>&#8599;</span>';
}
function formatContribution(value){return Math.abs(value)<.01&&value!==0?value.toExponential(2):value.toFixed(3);}
function renderExplanations(e){
 window.dispatchEvent(new CustomEvent('spicescope:explanations',{detail:e}));
 for(const name of ['powder','colouring']){const cam=e.cams[name];$(name+'CamTarget').textContent=label(cam.target);$(name+'CamBase').src=e.prepared_image;$(name+'CamOverlay').src=cam.map;$(name+'CamOverlay').hidden=!cam.has_positive_activation;$(name+'CamNote').textContent=cam.has_positive_activation?'Positive attribution for '+label(cam.target)+' on the prepared image.':'No positive attribution at this layer for this target.';}
 const mask=e.segmentation;$('maskOriginal').src=mask.original;$('maskBinary').src=mask.binary_mask;$('maskContour').src=mask.contour;$('maskPrepared').src=mask.prepared;$('maskCoverage').textContent=(mask.coverage*100).toFixed(1)+'% mask coverage';$('maskNote').textContent=mask.note+(!mask.roi_valid?' The ROI check did not pass; the pipeline used its full-image fallback.':'');
 const ig=e.colour_attribution;const max=Math.max(...ig.groups.map(g=>Math.abs(g.attribution)),1e-10);$('attributionBars').replaceChildren();
 for(const group of ig.groups){const row=document.createElement('div');row.className='attribution-row';const title=document.createElement('span');title.textContent=group.name;const track=document.createElement('div');track.className='signed-track';const fill=document.createElement('span');fill.className=group.attribution>=0?'positive':'negative';const width=Math.abs(group.attribution)/max*50;fill.style.width=width+'%';fill.style.left=(group.attribution>=0?50:50-width)+'%';track.append(fill);const value=document.createElement('strong');value.textContent=(group.attribution>0?'+':'')+formatContribution(group.attribution);row.append(title,track,value);$('attributionBars').append(row);}
 $('igQuality').textContent='Integration check: '+(ig.completeness_passed?'passed':'approximation needs caution')+' | residual '+ig.completeness_residual.toExponential(2)+' logit units | '+ig.integration_steps+' steps. Histogram bars sum signed bin contributions.';
 $('featureRows').replaceChildren();for(const feature of ig.features){const row=document.createElement('tr');for(const value of [feature.name,formatContribution(feature.value),(feature.attribution>0?'+':'')+formatContribution(feature.attribution)]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}$('featureRows').append(row);}
 $('explainTiming').textContent='Explanations computed locally in '+e.elapsed_seconds.toFixed(2)+' s';$('explainContent').hidden=false;$('explainButton').textContent='Regenerate explanations';
}
$('heatOpacity').oninput=()=>{$('explainContent').style.setProperty('--heat-opacity',Number($('heatOpacity').value)/100);$('opacityValue').textContent=$('heatOpacity').value+'%';};
$('explainButton').onclick=async()=>{
 if(!result||!selectedFile||busy)return;
 busy=true;syncButton();$('explainButton').disabled=true;$('explainProgress').hidden=false;$('explainError').hidden=true;$('explainSection').setAttribute('aria-busy','true');
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),180000);
 try{const form=new FormData();form.append('file',selectedFile);const response=await fetch('/api/explain',{method:'POST',body:form,signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(data.detail||'Explanations could not be generated.');if(data.powder!==result.powder||data.colouring!==result.colouring)throw Error('The explanation targets differ from this prediction. Please analyze again.');result.explanations=data.explanations;renderExplanations(data.explanations);}
 catch(error){$('explainError').textContent=error.name==='AbortError'?'Explanation timed out. CPU processing can take longer; please try again.':requestError(error);$('explainError').hidden=false;}
 finally{clearTimeout(timeout);busy=false;syncButton();$('explainButton').disabled=false;$('explainProgress').hidden=true;$('explainSection').setAttribute('aria-busy','false');}
};
async function downloadOverlay(name){
 if(!result?.explanations)return;const e=result.explanations,base=new Image(),heat=new Image();base.src=e.prepared_image;heat.src=e.cams[name].map;
 try{await Promise.all([base.decode(),heat.decode()]);const canvas=document.createElement('canvas');canvas.width=base.naturalWidth;canvas.height=base.naturalHeight;const context=canvas.getContext('2d');context.drawImage(base,0,0);if(e.cams[name].has_positive_activation){context.globalAlpha=Number($('heatOpacity').value)/100;context.drawImage(heat,0,0);}const a=document.createElement('a');a.href=canvas.toDataURL('image/png');a.download='SpiceScope_'+name+'_'+e.cams[name].target+'_GradCAM.png';a.click();}catch{$('explainError').textContent='Overlay download could not finish. Please regenerate explanations.';$('explainError').hidden=false;}
}
$('downloadPowderCam').onclick=()=>downloadOverlay('powder');$('downloadColouringCam').onclick=()=>downloadOverlay('colouring');

// A real 3D particle scene, projected onto Canvas. No remote graphics dependency.
(()=>{
const canvas=$('spiceScene'),host=$('heroArt'),ctx=canvas.getContext('2d');if(!ctx)return;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let w=400,h=360,dpr=1,mouseX=0,mouseY=0,rotation=0,visible=true;
let randomState=42;function random(){randomState=(randomState*1664525+1013904223)>>>0;return randomState/4294967296;}
const grains=[];
for(let i=0;i<2600;i++){const a=random()*Math.PI*2,r=Math.sqrt(random())*1.12;const mound=0.12+0.66*Math.pow(Math.max(0,1-r/1.12),1.35);grains.push({x:Math.cos(a)*r,y:-mound+random()*.12,z:Math.sin(a)*r,size:.7+random()*1.15,tone:random()});}
const flecks=Array.from({length:30},()=>({x:(random()-.5)*3.6,y:-.3-random()*1.3,z:(random()-.5)*2.5,size:random()+.7,tone:random()}));
function resize(){const box=host.getBoundingClientRect();w=box.width;h=box.height;dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);}
new ResizeObserver(resize).observe(host);resize();
host.addEventListener('pointermove',e=>{const r=host.getBoundingClientRect();mouseX=(e.clientX-r.left)/r.width-.5;mouseY=(e.clientY-r.top)/r.height-.5;});host.addEventListener('pointerleave',()=>{mouseX=0;mouseY=0;});
new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;}).observe(host);
function point(x,y,z){const a=rotation+mouseX*.32;const c=Math.cos(a),s=Math.sin(a),rx=x*c-z*s,rz=x*s+z*c;const tilt=.58+mouseY*.13;const py=y*Math.cos(tilt)-rz*Math.sin(tilt),pz=y*Math.sin(tilt)+rz*Math.cos(tilt);const perspective=4.9/(4.9+pz);const scale=Math.min(w*.27,120);return{x:w*.5+rx*scale*perspective,y:h*.57+py*scale*perspective,z:pz,k:perspective};}
function ring(radius,y,color,width){ctx.beginPath();for(let i=0;i<=100;i++){const a=i/100*Math.PI*2,p=point(Math.cos(a)*radius,y,Math.sin(a)*radius);if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);}ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();}
function draw(){ctx.clearRect(0,0,w,h);const shadow=ctx.createRadialGradient(w*.5,h*.78,0,w*.5,h*.78,w*.3);shadow.addColorStop(0,'rgba(57,65,30,.14)');shadow.addColorStop(1,'rgba(57,65,30,0)');ctx.save();ctx.translate(w*.5,h*.78);ctx.scale(1,.25);ctx.translate(-w*.5,-h*.78);ctx.fillStyle=shadow;ctx.fillRect(0,0,w,h*4);ctx.restore();
// Ceramic bowl, constructed from stacked 3D rings.
for(let j=0;j<34;j++){const t=j/33;const radius=.78+.44*Math.sin(t*Math.PI/2);ring(radius,.49-t*.47,`hsl(${39+t*5},${20+t*4}%,${70+t*21}%)`,3.8);}
// Continuous mound surface below individual grains.
const faces=[];const rings=18,slices=52;
function surface(r,a){return point(Math.cos(a)*r,-(.12+.66*Math.pow(Math.max(0,1-r/1.12),1.35)),Math.sin(a)*r);}
for(let j=0;j<rings;j++){for(let k=0;k<slices;k++){const r1=j/rings*1.12,r2=(j+1)/rings*1.12,a1=k/slices*Math.PI*2,a2=(k+1)/slices*Math.PI*2;const p=[surface(r1,a1),surface(r2,a1),surface(r2,a2),surface(r1,a2)];faces.push({p,z:p.reduce((s,v)=>s+v.z,0)/4,light:42+7*Math.cos(a1+rotation)+3*(1-j/rings)});}}
faces.sort((a,b)=>b.z-a.z);for(const face of faces){ctx.beginPath();face.p.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();ctx.fillStyle='hsl(29,78%,'+face.light+'%)';ctx.fill();}
const points=grains.map(g=>({...point(g.x,g.y,g.z),grain:g})).sort((a,b)=>b.z-a.z);
for(const p of points){const g=p.grain;const light=43+g.tone*21-(p.z*.9);ctx.fillStyle=`hsl(${23+g.tone*15},${68+g.tone*18}%,${light}%)`;ctx.beginPath();ctx.ellipse(p.x,p.y,g.size*p.k,g.size*.65*p.k,rotation+g.tone*6,0,Math.PI*2);ctx.fill();}
ring(1.2,.015,'#ded8bb',3);ring(1.23,.005,'#faf7e9',3);ring(1.18,.035,'#adac8e',.8);
for(const g of flecks){const floatY=g.y+Math.sin(rotation*2+g.x*4)*.05,p=point(g.x,floatY,g.z);ctx.fillStyle=`rgba(185,118,54,${.18+g.tone*.32})`;ctx.beginPath();ctx.arc(p.x,p.y,g.size*p.k,0,Math.PI*2);ctx.fill();}
}
let last=0;function frame(t){if(visible&&!document.hidden&&t-last>30){if(!reduced)rotation+=.0035;draw();last=t;}if(!reduced)requestAnimationFrame(frame);}
if(reduced){draw();new ResizeObserver(draw).observe(host);}else requestAnimationFrame(frame);
})();
