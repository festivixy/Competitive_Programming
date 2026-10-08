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
#define dbg(x);l
int c[N];
ll f[N];

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, q; cin >> n >> q;
    int m = 0; ll s = 0;
    FOR(i,0,n){
        int x;cin >> x;
        c[x]++;
        m = max(m,x);
        s += x;
    }
    FORR(v,1,m+1) c[v] += c[v+1];
    FOR(t,1,m+1) for(int j = t; j <= m; j += t) f[t] += c[j];


    while(q--){
        ll k; cin >> k;
        bool ok = k >= m ? k <= s : f[(m+k-1)/k] >= k;
        cout << (ok ? "YES" : "NO") << '\n';
    }
}
