import math
import torch
from torch import nn
from torch.nn import functional as F
import kornia.color as colour

class RGBNormalization(nn.Module):
    def __init__(self):
        super().__init__(); self.register_buffer('mean',torch.tensor([.485,.456,.406]).view(1,3,1,1))
        self.register_buffer('std',torch.tensor([.229,.224,.225]).view(1,3,1,1))
    def forward(self,x): return (x-self.mean)/self.std

def colour_representations(x):
    x=x.float()
    hsv=colour.rgb_to_hsv(x); hsv=torch.cat([hsv[:,:1]/(2*math.pi),hsv[:,1:]],dim=1)
    lab=colour.rgb_to_lab(x)
    lab=torch.cat([lab[:,:1]/50-1,lab[:,1:]/128],dim=1)
    return x*2-1,hsv*2-1,lab

class ColourFusion(nn.Module):
    def __init__(self,channels=12,gated=True):
        super().__init__(); self.gated=gated
        self.projections=nn.ModuleList([nn.Sequential(nn.Conv2d(3,channels,1),nn.GELU()) for _ in range(3)])
        self.gate=nn.Sequential(nn.Linear(3*channels,channels),nn.GELU(),nn.Linear(channels,3))
        self.adapter=nn.Conv2d(channels,3,1)
        nn.init.zeros_(self.adapter.weight); nn.init.zeros_(self.adapter.bias)
        self.last_gates=None
    def forward(self,x):
        assert x.ndim==4 and x.shape[1]==3
        with torch.autocast(device_type=x.device.type,enabled=False): reps=colour_representations(x)
        features=[projection(rep) for projection,rep in zip(self.projections,reps)]
        context=torch.cat([f.mean((2,3)) for f in features],dim=1)
        gates=self.gate(context).softmax(dim=1) if self.gated else context.new_full((x.shape[0],3),1/3)
        fused=sum(f*gates[:,i,None,None,None] for i,f in enumerate(features))
        self.last_gates=gates.detach()
        adapted=x+.1*torch.tanh(self.adapter(fused))
        assert adapted.shape==x.shape
        return adapted

class OrdinalHead(nn.Module):
    def __init__(self,features):
        super().__init__(); self.score=nn.Linear(features,1,bias=False)
        # Start with thresholds [-1, 1]. A gap <= log(4) makes Medium
        # unable to be the uniquely most probable class under argmax.
        # Both thresholds remain learnable; no predictions are forced.
        initial_gap=2.0
        self.first=nn.Parameter(torch.tensor(-initial_gap/2))
        self.raw_gap=nn.Parameter(torch.tensor(math.log(math.expm1(initial_gap-1e-4))))
    def forward(self,x):
        thresholds=torch.stack([self.first,self.first+F.softplus(self.raw_gap)+1e-4])
        return self.score(x)-thresholds

def ordinal_targets(y): return (y[:,None]>torch.arange(2,device=y.device)[None,:]).float()
def ordinal_loss(logits,y): return F.binary_cross_entropy_with_logits(logits,ordinal_targets(y))
def class_probabilities(logits,ordinal=True):
    if not ordinal: return logits.float().softmax(1)
    cumulative=logits.float().sigmoid()
    return torch.stack([1-cumulative[:,0],cumulative[:,0]-cumulative[:,1],cumulative[:,1]],dim=1)

class ResearchModel(nn.Module):
    def __init__(self,backbone,features,fusion=None,ordinal=True,is_vmamba=False):
        super().__init__(); self.backbone=backbone; self.fusion=fusion
        self.normalization=RGBNormalization(); self.ordinal=ordinal; self.is_vmamba=is_vmamba
        self.head=OrdinalHead(features) if ordinal else nn.Linear(features,3)
        self.frozen_backbone=False; self.frozen_modules=[]
    def features(self,x):
        if self.fusion is not None: x=self.fusion(x)
        return self.backbone(self.normalization(x))
    def forward(self,x): return self.head(self.features(x))
    def train(self,mode=True):
        super().train(mode)
        if mode:
            if self.frozen_backbone: self.backbone.eval()
            for module in self.frozen_modules: module.eval()
        return self