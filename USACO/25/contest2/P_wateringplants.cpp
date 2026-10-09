#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=5e5+5;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

int w[N], c[N];  ll x[N];
// int f[1000001], g[1000001];
// ll f[1000001], g[1000001];
// int len[4*N], r[4*N];
int len[4*N];  ll r[4*N];

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n; cin >> n;
    FOR(i,1,n+1) cin >> w[i];
    FOR(i,1,n) cin >> c[i];

    // FOR(i,2,n+1){
    //     FOR(j,0,i) x[j]=0;
    //     FOR(j,1,i+1){
    //         ll d=w[j]-x[j-1];
    //         if(d>0) x[j<i ? j : i-1]+=d;
    //     }
    //     ll ans=0;
    //     FOR(j,1,i) ans+=c[j]*x[j];
    //     cout << ans << '\n';
    // }

    // int W=*max_element(w+1,w+n+1);
    // FOR(x,1,W+1) g[x]=1e9;
    // FOR(i,1,n+1){
    //     if(i>1) cout << g[w[i]] << '\n';
    //     if(i==n) break;
    //     FOR(y,0,W+1) f[y]=c[i]*y+g[max(0,w[i]-y)];
    //     g[W]=f[W];
    //     FORR(x,0,W) g[x]=min(f[x],g[x+1]);
    // }

    // vector<pair<int,ll>> s={{1000000,1000001}}, t;
    // ll v=0;
    // FOR(i,1,n+1){
    //     int tl=0;  ll ar=0;
    //     t.clear();
    //     for(auto [l,k]:s){
    //         int u=min(l,w[i]-tl);
    //         if(u<=0) break;
    //         t.push_back({u,k}), tl+=u, ar+=u*k;
    //     }
    //     v+=ar;
    //     if(i>1) cout << v << '\n';
    //     if(i==n) break;
    //     s.clear();
    //     int z=0, j=sz(t)-1;
    //     for(; j>=0 && c[i]-t[j].second<=0; j--){
    //         v+=t[j].first*(c[i]-t[j].second);
    //         z+=t[j].first;
    //     }
    //     if(z) s.push_back({z,0});
    //     for(; j>=0; j--) s.push_back({t[j].first,c[i]-t[j].second});
    //     s.push_back({1000000,c[i]});
    // }

    // deque on e[0]..e[1] by stride d, slope=a*r+b, v=g(0), ar=sum len*slope
    int e[2]={2*N,2*N}, d=1, a=1, tl=1e6;
    ll b=0, ar=1000000LL*1000001, v=0;
    len[2*N]=1e6, r[2*N]=1e6+1;
    FOR(i,1,n+1){
        // while(tl-len[e[1]]>=w[i]){
        while((e[1]-e[0])*d>=0 && tl-len[e[1]]>=w[i]){
            tl-=len[e[1]];
            ar-=len[e[1]]*(a*r[e[1]]+b);
            e[1]-=d;
        }
        if(tl>w[i]){
            ar-=(tl-w[i])*(a*r[e[1]]+b);
            len[e[1]]-=tl-w[i];
            tl=w[i];
        }
        v+=ar;
        if(i>1) cout << v << '\n';
        if(i==n) break;
        swap(e[0],e[1]), d=-d;
        // b=c[i]-b;
        a=-a, b=c[i]-b;
        ar=(ll)c[i]*tl-ar;
        e[1]+=d, len[e[1]]=1e6, r[e[1]]=a*(c[i]-b);
        tl+=1e6, ar+=1000000LL*c[i];
        int z=0;
        for(ll s; (s=a*r[e[0]]+b)<=0; e[0]+=d){
            v+=len[e[0]]*s;
            ar-=len[e[0]]*s;
            z+=len[e[0]];
        }
        if(z) e[0]-=d, len[e[0]]=z, r[e[0]]=-a*b;
    }
}
