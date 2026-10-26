"""Controlled two-compartment model, not a contest/field-data experiment.

V dc/dt = (-Q(c1-c2), Q(c1-c2)); constant positive volumes,
well-mixed conservative exchange and nonnegative Q. Total mass is invariant.
Exact difference decay closes this linear model; backward Euler is a mature
positivity-preserving repair for an overlarge explicit step, not a new algorithm.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np


def generator(volumes=(1.,1.),flow=.8):
    v=np.asarray(volumes,dtype=float)
    if v.shape!=(2,) or not np.isfinite(v).all() or (v<=0).any() or not math.isfinite(flow) or flow<0:
        raise ValueError('positive finite volumes and nonnegative finite exchange flow required')
    a,b=flow/v
    return np.array([[-a,a],[b,-b]])


def exact(times,volumes=(1.,1.),flow=.8,initial=(1.,0.)):
    generator(volumes,flow)
    v=np.asarray(volumes); c=np.asarray(initial,dtype=float)
    if c.shape!=(2,) or not np.isfinite(c).all() or (c<0).any(): raise ValueError('nonnegative finite concentrations required')
    equilibrium=float(v@c/v.sum()); difference=(c[0]-c[1])*np.exp(-flow*(1/v).sum()*np.asarray(times))
    return np.column_stack((equilibrium+v[1]/v.sum()*difference,equilibrium-v[0]/v.sum()*difference))


def solve(step,method,volumes=(1.,1.),flow=.8,initial=(1.,0.),duration=6.):
    a=generator(volumes,flow)
    if not math.isfinite(step) or step<=0 or duration<0: raise ValueError('valid time domain required')
    c0=exact([0.],volumes,flow,initial)[0]
    n=int(round(duration/step))
    if not math.isclose(n*step,duration): raise ValueError('controlled grid must divide duration exactly')
    times=np.linspace(0,duration,n+1); values=[c0]
    for _ in range(n):
        if method=='explicit': value=(np.eye(2)+step*a)@values[-1]
        elif method=='implicit': value=np.linalg.solve(np.eye(2)-step*a,values[-1])
        else: raise ValueError('unsupported controlled solver')
        values.append(value)
    values=np.asarray(values); truth=exact(times,volumes,flow,initial)
    mass=values@np.asarray(volumes)
    return {'step':step,'method':method,'volumes':list(volumes),'flow':flow,'times':times.tolist(),
            'values':values.tolist(),'exact':truth.tolist(),'minimum':float(values.min()),
            'mass':mass.tolist(),'mass_error':float(np.max(abs(mass-mass[0]))),
            'max_error':float(np.max(abs(values-truth))),
            'positivity_condition':bool(step*max(flow/np.asarray(volumes))<=1),
            'roundoff_mass_bound':float(32*np.finfo(float).eps*(n+1)*max(1,abs(mass[0])))}


def study():
    explicit=solve(2.,'explicit'); implicit=solve(2.,'implicit')
    refinement=[solve(h,'implicit') for h in (1.,.5,.25,.125,.0625,.03125)]
    unequal=solve(.125,'implicit',(1.,3.))
    # Only observing invariant total mass cannot identify Q.
    same_total=[exact([0.,1.,2.],flow=q)@np.array([1.,1.]) for q in (.2,.8,1.5)]
    d=exact([1.],flow=.8)[0]; inferred=-math.log(d[0]-d[1])/2
    checks=[{'purpose':'overlarge explicit step violates nonnegative concentration','relation':'exact','actual':explicit['minimum']<0,'expected':True},
            {'purpose':'backward Euler preserves nonnegativity','relation':'exact','actual':implicit['minimum']>=0,'expected':True},
            {'purpose':'implicit numerical mass error is within accumulated floating-point allowance','relation':'close','actual':implicit['mass_error'],'expected':0,'atol':implicit['roundoff_mass_bound'],'rtol':0,'tolerance_basis':'32 machine eps per grid step times mass scale; numerical rounding, not physical inference'},
            {'purpose':'refinement decreases measured global error','relation':'exact','actual':all(refinement[i+1]['max_error']<refinement[i]['max_error'] for i in range(len(refinement)-1)),'expected':True},
            {'purpose':'unequal-volume model conserves weighted not unweighted mass','relation':'close','actual':unequal['mass_error'],'expected':0,'atol':unequal['roundoff_mass_bound'],'rtol':0,'tolerance_basis':'accumulated arithmetic allowance for weighted mass on this grid'},
            {'purpose':'total mass alone carries no flow identification','relation':'exact','actual':all(np.allclose(x,1,rtol=0,atol=8*np.finfo(float).eps) for x in same_total),'expected':True},
            {'purpose':'difference measurement identifies constant flow','relation':'close','actual':inferred,'expected':.8,'atol':16*np.finfo(float).eps,'rtol':0,'tolerance_basis':'floating-point logarithm on an exact noiseless controlled observation'}]
    return {'scope':'hypothetical conservative linear model, not measured data or original-algorithm claim','explicit':explicit,'implicit':implicit,
            'refinement':refinement,'unequal':unequal,'observed_value':implicit['values'][-1][0],
            'inferred_flow':inferred,'checks':checks}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(study(),indent=2),encoding='utf-8')
