#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=3e5+5;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n; string s;
    cin >> n >> s;
    if(s[0]!='+' || s[n-1]!='-'){
        cout << "NO\n"; return 0;
    }
    cout << "YES\n";
    FOR(i,0,n)if(s[i]=='+') cout << i << ' ';
    FORR(i,0,n) if(s[i]=='-') cout << i << ' ';
    cout << '\n';
}
