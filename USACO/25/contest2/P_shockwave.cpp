#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=1e5+5;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

int n;  ll p[N],A[N],B[N],st[17][N];

bool fit(ll K, int c){
    ll a=0, b=0;
    FOR(i,0,n){
        ll w = c<0 ? 0 : abs(i-c);
        int D=2*i-n+1;
        // a@0, b@n-1: F(i)=K(n-1-i)+a*D=K*i+b*(-D)
        if(D>0){
            ll P=p[i]-K*(n-1-i)-w;
            if(P>0) a = max(a,(P+D-1)/D);
        }else if(D<0){
            ll P=p[i]-K*i-w;
            if(P>0) b = max(b,(P-D-1)/-D);
        }else if(K*i+w < p[i]) return false;
    }
    return a+b <= K;
}

// bool feas(ll K){
//     if(fit(K,-1)) return true;
//     FOR(c,0,n) if(K && fit(K-1,c)) return true;
//     return false;
// }

void build(ll m, ll* X){
    int L=__lg(n)+1;
    FOR(k,0,L) fill(st[k],st[k]+n,0);
    FOR(i,0,n){
        int D=2*i-n+1;
        ll P=p[i]-m*(n-1-i);
        if(D<=0 || P<=0) continue;
        // ceil((P-|i-c|)/D)>=v <=> |i-c|<=P-(v-1)D-1
        ll v=(P+D-1)/D, d=P-(v-1)*D-1;
        // for(ll v=1, d=P-1; d>=0; v++, d-=D){
        for(; v>0; v--, d+=D){
            int l=max(0LL,i-d), r=min((ll)n-1,i+d), k=__lg(r-l+1);
            st[k][l]=max(st[k][l],v), st[k][r-(1<<k)+1]=max(st[k][r-(1<<k)+1],v);
            if(d>=i) break;
        }
    }
    FORR(k,1,L) FOR(x,0,n-(1<<k)+1){
        st[k-1][x]=max(st[k-1][x],st[k][x]);
        st[k-1][x+(1<<(k-1))]=max(st[k-1][x+(1<<(k-1))],st[k][x]);
    }
    FOR(c,0,n) X[c]=st[0][c];
}

void solve(){
    cin >> n;
    FOR(i,0,n) cin >> p[i];
    // ll ans=0;
    // while(1){
    //     int j=max_element(p,p+n)-p;
    //     if(p[j]<=0) break;
    //     int x = j<n-1-j ? n-1 : 0;
    //     FOR(i,0,n) p[i]-=abs(i-x);
    //     ans++;
    // }
    // cout << ans << '\n';

    ll mx=*max_element(p,p+n);
    // ll lo=0, hi=(ll)2e18;
    ll lo=0, hi=2*((mx+n-2)/(n-1));
    while(lo<hi){
        ll mid=(lo+hi)/2;
        // if(feas(mid)) hi=mid;
        if(fit(mid,-1)) hi=mid;
        else lo=mid+1;
    }
    // cout << lo << '\n';
    ll E=lo, m=E-2;
    if(E<2){cout << E << '\n'; return;}

    // int c=min_element(p,p+n)-p;
    // if(fit(m,c) || fit(m,(n-1)/2)) E--;
    // cout << E << '\n';
    build(m,A);
    reverse(p,p+n);
    build(m,B);
    int h=(n-1)/2;
    // center: |h-c|>=p_h-m*h
    ll q = n&1 ? p[h]-m*h : 0;
    bool f=0;
    // FOR(c,0,n) if(A[c]+B[c]<=m) f=1;
    // FOR(c,0,n) if(A[c]+B[n-1-c]<=m) f=1;
    FOR(c,0,n) if(A[c]+B[n-1-c]<=m && abs(h-c)>=q) f=1;
    cout << E-f << '\n';
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t; cin >> t;
    while(t--) solve();
}
