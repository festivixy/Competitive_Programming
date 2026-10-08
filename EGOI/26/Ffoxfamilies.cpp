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

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n; cin >> n;
    map<ll,array<ll,3>> b;

    FOR(i,0,n){
        int l, r; cin >> l >> r;
        ll k = (ll)l<<18|(262143-r);
        ll s = k, e = k, mn = r, mx = r;
        auto it = b.upper_bound(k);
        while(it != b.begin()){
            auto j = prev(it);
            if(j->second[0] < k && j->second[2] < r) break;
            s = j->first;
            e = max(e,j->second[0]);
            mn = min(mn,j->second[1]), mx = max(mx,j->second[2]);
            b.erase(j);
        }
        while(it != b.end() && it->second[1] <= r){
            e = it->second[0];
            mn = min(mn,it->second[1]), mx = max(mx,it->second[2]);
            it = b.erase(it);
        }
        b[s] = {e,mn,mx};
        cout << sz(b) << '\n';
    }
}
