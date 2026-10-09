#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
//const int N=755;
const int N=750;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

int a[N][N];
//int par[N],ed[N],st[N];
//int P[N][N],dp[N][N],h[N][N];
int P[N][N],dp[N][N];

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n; cin >> n;
    FOR(j,2,n+1) FOR(i,1,j) cin >> a[i][j];

    //ll ans = 0;
    //int m=0;
    //st[m++]=1;
    //FOR(v,2,n+1){
    //    //int b=INT_MAX;
    //    //FOR(p,1,v) b = min(b, max(a[p][v],0));
    //    //ans += b;
    //    int b=INT_MAX, p=0;
    //    FOR(k,0,m) if(max(a[st[k]][v],0) <= b) b=max(a[st[k]][v],0),p=st[k];
    //    ans += b;
    //    while(st[m-1] != p) m--;
    //    st[m++]=v;
    //    par[v]=p;
    //}

    //FOR(v,1,n+1) ed[v]=v;
    //FORR(v,2,n+1) ed[par[v]] = max(ed[par[v]],ed[v]);
    //FOR(j,2,n+1) FOR(i,1,j) if(a[i][j]<0 && j>ed[i]) ans -= a[i][j];
    //cout << ans << '\n';
    FOR(i,1,n+1) FOR(j,1,n+1) P[i][j] = (i<j && a[i][j]<0 ? -a[i][j] : 0)+P[i-1][j]+P[i][j-1]-P[i-1][j-1];
    auto R=[&](int u1,int u2,int v1,int v2){
        return P[u2][v2]-P[u1-1][v2]-P[u2][v1-1]+P[u1-1][v1-1];
    };

    //FORR(l,1,n+1){
    //    FORR(x,l+1,n+1){
    //        FOR(r,x,n+1){
    //            int b=INT_MAX;
    //            FOR(e,x,r+1) b = min(b, dp[x][e]+max(a[l][x],0)+(e<r ? R(x,e,e+1,r)+h[e+1][r] : 0));
    //            h[x][r]=b;
    //        }
    //    }
    //    dp[l][l]=0;
    //    FOR(r,l+1,n+1) dp[l][r]=h[l+1][r];
    //}
    FORR(l,1,n+1){
        dp[l][l]=0;
        FOR(r,l+1,n+1){
            int b=INT_MAX;
            //FOR(c,l+1,r+1) b = min(b, dp[l][c-1]+dp[c][r]+max(a[l][c],0)+R(l+1,c-1,c+1,r));
            //FOR(c,l+1,r+1) b = min(b, dp[l][c-1]+dp[c][r]+max(a[l][c],0)+R(l,c-1,c,r));
            FOR(c,l+1,r+1) b = min(b, dp[l][c-1]+dp[c][r]+max(a[l][c],0)+R(l+1,c-1,c,r));
            dp[l][r]=b;
        }
    }
    cout << dp[1][n] << '\n';
}
