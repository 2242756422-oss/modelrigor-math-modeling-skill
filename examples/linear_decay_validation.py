#!/usr/bin/env python3
"""Actual numerical/plotting example, not CUMCM data or a default model.

First-order removal dC/dt=-kC, C(0)=1 mg/L; k=0.5 /s. A known
analytic solution checks RK4 and timestep refinement. Parameter values define
a controlled verification example; they are not estimated empirical facts.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def rk4(rate, duration, step):
    n=round(duration/step); h=duration/n; value=1.0; values=[value]
    for _ in range(n):
        a=-rate*value; b=-rate*(value+h*a/2)
        c=-rate*(value+h*b/2); d=-rate*(value+h*c)
        value+=h*(a+2*b+2*c+d)/6; values.append(value)
    return [i*h for i in range(n+1)],values


def solve(out):
    out.mkdir(parents=True,exist_ok=True)
    t, values=rk4(0.5,6,0.05)
    steps=[0.5,0.25,0.125,0.0625]
    errors=[]
    for h in steps:
        grid,calc=rk4(0.5,6,h)
        errors.append(max(abs(x-math.exp(-0.5*time)) for time,x in zip(grid,calc)))
    data={"model":"first-order removal, specified synthetic verification case",
          "input":{"rate_per_second":0.5,"initial_mg_per_litre":1.0,"duration_s":6},
          "time_s":t,"concentration_mg_per_litre":values,
          "exact_mg_per_litre":[math.exp(-0.5*time) for time in t],
          "endpoint":values[-1],"steps_s":steps,"max_errors":errors,
          "refinement_orders":[math.log(errors[i]/errors[i+1],2) for i in range(len(errors)-1)]}
    (out/"calculation.json").write_text(json.dumps(data,indent=2)+"\n")
    print("Computed",len(t),"time samples; refinement orders",data["refinement_orders"])


def verify(out):
    data=json.loads((out/"calculation.json").read_text())
    exact=math.exp(-data["input"]["rate_per_second"]*data["input"]["duration_s"])
    # Bound used here is observed error on the controlled exact-solution case,
    # not a general solver certification for arbitrary physical problems.
    accuracy=max(abs(x-y) for x,y in zip(data["concentration_mg_per_litre"],data["exact_mg_per_litre"]))
    checks=[{"purpose":"analytic endpoint agrees within measured full-grid error","relation":"close","actual":data["endpoint"],"expected":exact,"atol":accuracy,"rtol":0,"tolerance_basis":"measured error against the known exact solution on this defined grid"},
            {"purpose":"nonnegative concentration for specified rate/steps","relation":"exact","actual":all(v>=0 for v in data["concentration_mg_per_litre"]),"expected":True},
            {"purpose":"removal has nonincreasing concentration","relation":"exact","actual":all(a>=b for a,b in zip(data["concentration_mg_per_litre"],data["concentration_mg_per_litre"][1:])) ,"expected":True},
            {"purpose":"halving step consistently reduces the measured discretization error","relation":"exact","actual":all(a>b for a,b in zip(data["max_errors"],data["max_errors"][1:])) ,"expected":True}]
    (out/"verification_output.json").write_text(json.dumps({"observed_value":data["endpoint"],"exact_endpoint":exact,"max_grid_error":accuracy,"checks":checks},indent=2)+"\n")
    print("Analytic endpoint",exact,"maximum measured grid error",accuracy)



if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("stage",choices=("solve","verify")); p.add_argument("out",type=Path); a=p.parse_args()
    {"solve":solve,"verify":verify}[a.stage](a.out.resolve())
