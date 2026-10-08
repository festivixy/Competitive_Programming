#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=2e5+5;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

int t[N],cnt[N],lst[N];
bool on[N];

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, d; cin >> n >> d;
    FOR(i,1,n+1) cin >> t[i];
    FOR(i,1,n+2) on[i] = t[i]<t[i-1];

    FOR(i,0,d){
        char c; int r; cin >> c >> r; r++;
        if(c == '?'){cout << cnt[r]+on[r]*(i+1-lst[r]) << '\n'; continue;}
        int x;cin >> x;
        for(int p = r; p <= r+1; p++){
            cnt[p] += on[p]*(i+1-lst[p]);
            lst[p]=i+1;
        }
        t[r] = x;
        for(int p = r; p <= r+1; p++){
            on[p] = t[p]<t[p-1];
        }
    }


}
