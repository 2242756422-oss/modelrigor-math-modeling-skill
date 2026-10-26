#!/usr/bin/env python3
"""Plot-only dependency: typography changes do not invalidate solver results."""
import argparse
import json
from pathlib import Path

def plot(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullLocator
    data=json.loads((out/"calculation.json").read_text())
    # Final physical width is chosen for this two-task example, not a template
    # requirement for all figures. Shared typography, not a mandatory palette.
    with plt.rc_context({"font.size":9,"axes.labelsize":9,"axes.titlesize":10,
                         "legend.fontsize":8,"axes.linewidth":0.7,"lines.linewidth":1.3,
                         "savefig.facecolor":"white","font.family":"DejaVu Sans"}):
        fig,axes=plt.subplots(1,2,figsize=(160/25.4,70/25.4),layout="constrained")
        ax=axes[0]
        ax.plot(data["time_s"],data["exact_mg_per_litre"],color="#315B78",label="Analytic reference")
        ax.plot(data["time_s"][::12],data["concentration_mg_per_litre"][::12],linestyle="none",marker="o",mfc="white",mec="#A66536",ms=4,label="RK4 samples")
        ax.set(xlabel="Time (s)",ylabel="Concentration (mg/L)",title="a  Model response")
        ax.legend(frameon=False); ax.spines[["top","right"]].set_visible(False)
        ax=axes[1]
        ax.loglog(data["steps_s"],data["max_errors"],"o-",color="#315B78",ms=4,label="Measured maximum error")
        anchor=data["max_errors"][-1]; last=data["steps_s"][-1]
        ax.loglog(data["steps_s"],[anchor*(h/last)**4 for h in data["steps_s"]],"--",color="#777777",lw=1,label="Fourth-order reference")
        ax.set(xlabel="Timestep (s)",ylabel="Maximum absolute error (mg/L)",title="b  Discretization verification")
        ax.set_xticks(sorted(data["steps_s"]),labels=["0.0625","0.125","0.25","0.5"])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.legend(frameon=False,loc="upper left",fontsize=7.5)
        ax.spines[["top","right"]].set_visible(False)
        fig.savefig(out/"response_and_verification.png",dpi=300)
        fig.savefig(out/"response_and_verification.svg")
        # Separate 150-DPI preview at the same final physical dimensions.
        fig.savefig(out/"final_size_preview.png",dpi=150)
        plt.close(fig)
    print("Actual numerical data plotted as two evidence tasks, final width 160 mm")


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("out",type=Path); a=p.parse_args()
    plot(a.out.resolve())
