"""Read-only numerical checks supporting the 2026-09-15 methodology audit.

Run from any directory with the backend Python dependencies installed:
    python backend/scripts/handoff_methodology_audit.py --prod /path/to/snapshot.db

These are retrospective diagnostics, not a new confirmatory experiment.
Imports the current rating policy; preserve versions when comparing outputs.
Does not fit or run the proposed coordination experiment.
"""
import sys, sqlite3, json, argparse
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
from scipy.special import ndtr
from scipy.optimize import minimize_scalar
BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND / 'scripts'), str(BACKEND)]
from skill_dependent_variance_eval import build_dataset, mu_residual_correlation
from walkforward_session_eval import load_matches, assign_sessions

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--local', default=str(BACKEND / 'data/sc2mmr.db'))
parser.add_argument('--prod', required=True)
args = parser.parse_args()
paths = {'local': str(Path(args.local).resolve()), 'prod': str(Path(args.prod).resolve())}
print('Database paths:', paths)
cache={}
def losses(p,y):
    p=np.clip(p,1e-12,1-1e-12)
    return -y*np.log(p)-(1-y)*np.log1p(-p)
def ci(d,s):
    blocks=[np.where(s==v)[0] for v in np.unique(s)]
    rng=np.random.default_rng(42)
    out=[np.mean(d[np.concatenate([blocks[i] for i in rng.integers(len(blocks),size=len(blocks))])]) for _ in range(3000)]
    return [float(np.mean(d)), *np.quantile(out,[.025,.975]).tolist()]
for label,path in paths.items():
    c=sqlite3.connect('file:'+path+'?mode=ro',uri=True)
    usable=load_matches(c); s=np.array(assign_sessions(usable)); rows=build_dataset(usable)
    cutoff=int(len(set(s))*.75); train=s<cutoff; test=~train
    delta=np.array([sum(x.mu for x in r['t1r'])-sum(x.mu for x in r['t2r']) for r in rows])
    variance=np.array([sum(x.sigma**2 for x in r['t1r']+r['t2r']) for r in rows])
    n=np.array([len(r['t1r']+r['t2r']) for r in rows]); y=np.array([r['outcome'] for r in rows])
    def fit(kind):
        def prob(v):
            denom=variance*(1+v) if kind=='k' else variance+n*v*v if kind=='beta' else (variance+n*25)*v
            return ndtr(delta/np.sqrt(denom))
        bounds=(0,1000) if kind=='k' else (.001,100)
        opt=minimize_scalar(lambda v: losses(prob(v),y)[train].mean(),bounds=bounds,method='bounded')
        return opt.x,prob(opt.x)
    models={kind:fit(kind) for kind in ['k','beta','temperature']}
    baseline=ndtr(delta/np.sqrt(variance+n*25)); k11=ndtr(delta/np.sqrt(variance*12))
    print('\n',label,'usable',len(usable),'sessions',len(set(s)),'train/test',int(train.sum()),int(test.sum()),'test sessions',len(set(s[test])), 'test start',usable[np.flatnonzero(test)[0]][1])
    print('k grid train losses',[(k,round(float(losses(ndtr(delta/np.sqrt(variance*(1+k))),y)[train].mean()),7)) for k in [0,5,8,10,11,12,15,20,30,100,1000]])
    print('baseline train/test',losses(baseline,y)[train].mean(),losses(baseline,y)[test].mean())
    for kind,(param,p) in models.items():
        print(kind,'fit',param,'train/test LL',losses(p,y)[train].mean(),losses(p,y)[test].mean(),'LL improvement CI',ci((losses(baseline,y)-losses(p,y))[test],s[test]),'Brier',float(np.mean((p[test]-y[test])**2)))
    print('baseline Brier',float(np.mean((baseline[test]-y[test])**2)))
    for kind in ['beta','temperature']:
        print('k advantage over fitted '+kind,ci((losses(models[kind][1],y)-losses(models['k'][1],y))[test],s[test]))
    def pcorr(p):
        vals=defaultdict(list); mus=defaultdict(list)
        for i in np.flatnonzero(test):
            for sign,ids,rs in [(1,usable[i][3],rows[i]['t1r']),(-1,usable[i][5],rows[i]['t2r'])]:
                for pid,r in zip(ids,rs):
                    vals[pid].append(sign*(y[i]-p[i]));mus[pid].append(r.mu)
        ids=[pid for pid in vals if len(vals[pid])>=10]
        return len(ids),np.corrcoef([np.mean(mus[pid]) for pid in ids],[np.mean(vals[pid]) for pid in ids])[0,1]
    for title,p in [('baseline',baseline),('k11',k11)]:
        print(title,'actual heldout player correlation n>=10',pcorr(p),'script correlation',mu_residual_correlation([rows[i] for i in np.flatnonzero(test)],p[test]))
    hashes=dict(c.execute('select id,replay_hash from matches'))
    cache[label]={'all':{hashes[u[0]] for u in usable},'train':{hashes[usable[i][0]] for i in np.flatnonzero(train)},'test':{hashes[usable[i][0]] for i in np.flatnonzero(test)},'usable':usable,'s':s,'y':y,'models':models,'baseline':baseline}
    print('metrics coverage',c.execute('select count(*),count(distinct mp.match_id),sum(p.damage_dealt>0),sum(p.early_game_damage>0),sum(p.overall_impact>0),sum(p.team_fight_participation>0),sum(p.damage_timeline is not null and p.damage_timeline not in (\'{}\',\'null\')) from player_match_metrics p join match_players mp on mp.id=p.match_player_id join matches m on m.id=mp.match_id').fetchone())
    names=dict(c.execute('select id,name from players'))
    for pid,name in names.items():
        if name not in ['Stephan','ShadowDragon','DragonKing']:continue
        with_games=Counter();against_games=Counter();switch=defaultdict(lambda:defaultdict(set)); present=0
        for u,sid in zip(usable,s):
            if pid not in u[3]+u[5]:continue
            present+=1;own=u[3] if pid in u[3] else u[5];opp=u[5] if pid in u[3] else u[3]
            for i in own:
                if i!=pid:with_games[i]+=1;switch[sid][i].add('with')
            for i in opp:against_games[i]+=1;switch[sid][i].add('against')
        changes=[(sid,i) for sid,d in switch.items() for i,states in d.items() if len(states)==2]
        print('exposure',name,'matches',present,'sessions',len(switch),'switch sessions',len(set(x[0] for x in changes)),'receiver-session switches',len(changes),'receivers >=10 with and against',sum(v>=10 and against_games[i]>=10 for i,v in with_games.items()))
    c.close()
for subset in ['all','train','test']:
    a,b=cache['local'][subset],cache['prod'][subset]
    print('OVERLAP',subset,len(a),len(b),len(a&b),'local only',len(a-b),'prod only',len(b-a))
new=cache['prod']['all']-cache['local']['all']
c=sqlite3.connect('file:'+paths['prod']+'?mode=ro',uri=True); hashes=dict(c.execute('select id,replay_hash from matches'))
ix=np.array([i for i,u in enumerate(cache['prod']['usable']) if hashes[u[0]] in new])
print('new production matches',len(ix),'sessions',len(set(cache['prod']['s'][ix])))
