#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=1e4+5;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

const ll MOD=1e9+7;
vector<int> g[N];
vector<vector<int>> cy[N];
ll p[N],ar[N],en[N];
ll E[N],LV[N];
vector<ll> CE[N];
//int par[N],ord[N],vis[N];
int par[N],ord[N],dep[N],inc[N];

ll pw(ll b,ll e){
    ll r=1;
    for(b%=MOD; e; e>>=1, b=b*b%MOD) if(e&1) r=r*b%MOD;
    return r;
}

void solve(){
    int n, m; cin >> n >> m;
    //FOR(i,1,n+1) cin >> p[i], g[i].clear(), vis[i]=0, ar[i]=0;
    FOR(i,1,n+1) cin >> p[i], g[i].clear(), cy[i].clear(), dep[i]=-1, inc[i]=0, ar[i]=0;
    FOR(i,0,m){
        int a, b; cin >> a >> b;
        g[a].push_back(b);
        g[b].push_back(a);
    }

    int k=0;
    //auto dfs=[&](auto&&dfs,int v,int u)->void{
    //    vis[v]=1;
    //    par[v]=u;
    //    ord[k++]=v;
    //    for(int x : g[v]) if(!vis[x]) dfs(dfs,x,v);
    //};
    //dfs(dfs,1,0);
    auto dfs=[&](auto&&dfs,int v,int u,int d)->void{
        dep[v]=d;
        par[v]=u;
        ord[k++]=v;
        for(int x : g[v]){
            if(dep[x]<0) dfs(dfs,x,v,d+1);
            else if(x != u && dep[x]<dep[v]){
                vector<int> c;
                for(int y = v; y != x; y = par[y]) c.push_back(y), inc[y]=1;
                reverse(all(c));
                cy[x].push_back(c);
            }
        }
    };
    dfs(dfs,1,0,0);

    FORR(i,0,n){
        int v=ord[i], c=sz(g[v])-(v!=1), z=sz(cy[v]);
        CE[v].assign(z,0);
        if(!c){E[v]=1, LV[v]=0; continue;}
        ll q=(1-p[v]+MOD)%MOD;
        vector<ll> w(z), cf(z+1), es(z+1), tt(z+1);
        FOR(j,0,z){
            ll r=1;
            for(int x : cy[v][j]) r=r*LV[x]%MOD;
            w[j]=2*r%MOD;
        }
        cf[0]=1;
        FOR(j,0,z) cf[j+1]=cf[j]*(j+1)%MOD*q%MOD*pw(c-2*j,MOD-2)%MOD;
        es[0]=1;
        FOR(b,0,z) FORR(j,0,b+1) es[j+1]=(es[j+1]+es[j]*w[b])%MOD;

        ll e=0, lv=0;
        FOR(j,0,z+1){
            int kk=c-2*j;
            e=(e+cf[j]*es[j]%MOD*(kk ? p[v] : 1))%MOD;
            if(kk) tt[j]=cf[j]*q%MOD*pw(kk,MOD-2)%MOD;
            lv=(lv+es[j]*tt[j])%MOD;
        }
        FOR(b,0,z){
            ll y=1;
            FOR(j,0,z){
                if(j) y=(es[j]-w[b]*y%MOD+MOD)%MOD;
                CE[v][b]=(CE[v][b]+y*tt[j])%MOD;
            }
        }
        E[v]=e, LV[v]=lv;
    }

    ar[1]=1;
    FOR(i,0,n){
        //int v=ord[i], c=0;
        //for(int x : g[v]) if(par[x]==v) c++;
        //if(!c){en[v]=ar[v]; continue;}
        //en[v]=ar[v]*p[v]%MOD;
        //ll t=ar[v]*(1-p[v]+MOD)%MOD*pw(c,MOD-2)%MOD;
        //for(int x : g[v]) if(par[x]==v) ar[x]=t;
        //int v=ord[i], c=sz(g[v])-(v!=1);
        //if(!c){en[v]=ar[v]; continue;}
        //en[v]=ar[v]*p[v]%MOD;
        //ll t=ar[v]*(1-p[v]+MOD)%MOD*pw(c,MOD-2)%MOD;
        //for(int x : g[v]) if(par[x]==v && !inc[x]) ar[x]=t;
        //for(auto &cc : cy[v]){
        //    FOR(d,0,2){
        //        ll cur=t;
        //        FOR(j,0,sz(cc)){
        //            int x = d ? cc[sz(cc)-1-j] : cc[j];
        //            ar[x]=(ar[x]+cur)%MOD;
        //            cur=cur*(1-p[x]+MOD)%MOD*pw(sz(g[x])-1,MOD-2)%MOD;
        //        }
        //        en[v]=(en[v]+cur)%MOD;
        //    }
        //}
        int v=ord[i];
        en[v]=ar[v]*E[v]%MOD;
        for(int x : g[v]) if(par[x]==v && !inc[x]) ar[x]=ar[v]*LV[v]%MOD;
        FOR(b,0,sz(cy[v])){
            auto &cc=cy[v][b];
            FOR(d,0,2){
                ll cur=ar[v]*CE[v][b]%MOD;
                FOR(j,0,sz(cc)){
                    int x = d ? cc[sz(cc)-1-j] : cc[j];
                    ar[x]=(ar[x]+cur)%MOD;
                    cur=cur*LV[x]%MOD;
                }
            }
        }
    }

    FOR(i,1,n+1) cout << en[i] << " \n"[i==n];
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t; cin >> t;
    while(t--) solve();
}
