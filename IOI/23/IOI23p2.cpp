#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=260;

bool are_connected(vector<int> A,vector<int> B);

static bool cn(const vector<int>&a,const vector<int>&b){return are_connected(a,b);}
static bool cn(int x,int y){return are_connected({x},{y});}
static vector<int> cut(const vector<int>&v,int l,int r){return vector<int>(v.begin()+l,v.begin()+r+1);}

vector<int> longest_trip(int n,int d){
    vector<int> p,q;
    if(d==3){
        FOR(i,0,n) p.push_back(i);
        return p;
    }

    p={0}; q={1};
    int i=2;
    bool inv=false; // inv <=> p.back() !~ q.back()

    for(;;){
        if(q.empty()){
            if(i==n) return p;
            q.push_back(i++);
            inv=false;
            continue;
        }
        if(!inv){
            if(!cn(p.back(),q.back())){ inv=true; continue; }
            while(sz(q)){ p.push_back(q.back()); q.pop_back(); }
            continue;
        }
        if(i==n) break;

        if(i+1==n){
            int v=i++;
            if(cn(v,p.back())){ p.push_back(v); inv=false; }
            else q.push_back(v); // !~p.back() => ~q.back() by density
            continue;
        }

        int u=i,v=i+1; i+=2;
        if(cn(u,v)){
            if(cn(p.back(),u)){ p.push_back(u); p.push_back(v); }
            else{ q.push_back(u); q.push_back(v); }
            inv=false;
        }
        else if(!cn(u,p.back())){
            p.push_back(v); q.push_back(u); // u~q.back(), and uv,up.back() missing => v~p.back()
        }
        else if(cn(v,q.back())){
            p.push_back(u); q.push_back(v);
        }
        else{
            p.push_back(v); q.push_back(u); // v~p.back(), and uv,vq.back() missing => u~q.back()
        }
    }

    int s=sz(p),t=sz(q);
    vector<int> e1{p[0]},e2{q[0]};
    if(s>1) e1.push_back(p.back());
    if(t>1) e2.push_back(q.back());

    if(cn(e1,e2)){
        int x=p[0],y=q[0];
        if(s>1&&cn({p.back()},e2)) x=p.back();
        if(t>1&&!cn(x,q[0])) y=q.back();
        if(x==p[0]&&s>1) reverse(all(p));
        if(y==q.back()&&t>1) reverse(all(q));
        p.insert(p.end(),all(q));
        return p;
    }

    if(!cn(p,q)) return s>=t?p:q;

    int lo=0,hi=s-1;
    while(lo<hi){
        int mid=(lo+hi)/2;
        if(cn(cut(p,lo,mid),q)) hi=mid; else lo=mid+1;
    }
    int a=lo;

    lo=0; hi=t-1;
    while(lo<hi){
        int mid=(lo+hi)/2;
        if(cn({p[a]},cut(q,lo,mid))) hi=mid; else lo=mid+1;
    }
    int b=lo;

    // no endpoint edge + crossing edge exists => both paths are cycles, rotate freely
    vector<int> res=cut(p,a+1,s-1);
    FOR(j,0,a+1) res.push_back(p[j]);
    FOR(j,b,t) res.push_back(q[j]);
    FOR(j,0,b) res.push_back(q[j]);
    return res;
}