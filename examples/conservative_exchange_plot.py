"""Visualize actual study outputs; plot changes do not change solver code."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    data=json.loads(a.source.read_text()); a.out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    fig,axes=plt.subplots(1,2,figsize=(160/25.4,72/25.4),layout='constrained')
    left,right=axes
    explicit,implicit=data['explicit'],data['implicit']
    # Full baseline range shown, including physically impossible negatives.
    left.plot(explicit['times'],[x[0] for x in explicit['values']],'o--',color='#B45A45',label='Explicit coarse step',lw=1.2,ms=3)
    left.plot(implicit['times'],[x[0] for x in implicit['values']],'s-',color='#31688E',label='Backward Euler',lw=1.3,ms=3)
    fine=data['refinement'][-1]
    left.plot(fine['times'],[x[0] for x in fine['exact']],color='#333333',label='Exact linear model',lw=1.2)
    left.axhline(0,color='#999999',lw=.6); left.set(xlabel='Time (s)',ylabel='Concentration (kg/m³)',title='a  Feasibility and response')
    left.legend(frameon=False,fontsize=7,loc='lower left')
    hs=[x['step'] for x in data['refinement']]; errors=[x['max_error'] for x in data['refinement']]
    right.loglog(hs,errors,'o-',color='#31688E',lw=1.3,ms=4,label='Measured grid error')
    right.loglog(hs,[errors[-1]*h/hs[-1] for h in hs],':',color='#555555',lw=1,label='First order reference')
    right.set(xlabel='Time step (s)',ylabel='Max error (kg/m³)',title='b  Accuracy under refinement')
    right.set_xticks([.03125,.125,.5,1],labels=['0.03125','0.125','0.5','1']); right.xaxis.set_minor_locator(NullLocator())
    right.legend(frameon=False,fontsize=7)
    for suffix in ('png','svg'): fig.savefig(a.out/('exchange.'+suffix),dpi=300)
    fig.savefig(a.out/'final_size_preview.png',dpi=180)
