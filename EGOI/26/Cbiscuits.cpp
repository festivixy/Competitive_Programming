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

const int P=1<<17;
unsigned char o[2*P][51];
int s[2*P][51];

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, q;cin >> n >> q;

    auto leaf=[&](int v,int w){
        FOR(d,0,51)o[v][d]=abs(w-d),s[v][d]=min(w,d);
    };
    auto pull=[&](int v){
        int l=2*v,r=2*v+1;
        FOR(d,0,51){
            int x=o[r][d];
            o[v][d]=o[l][x];
            s[v][d]=s[r][d]+s[l][x];
        }
    };
    FOR(i,0,P){
        int w=0;if(i<n)cin>>w;leaf(P+i,w);
    }
    FORR(v,1,P) pull(v);
    cout<< s[1][0] << '\n';
    while(q--){
        int p, z;cin >> p >> z;
        leaf(P+p,z);
        for(int v=(P+p)>>1; v; v>>=1)pull(v);
        cout << s[1][0] << '\n';
    }
}
