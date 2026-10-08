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

int a[N],st[N],tb[N],ord[N],head[N],nxt[2*N],to[2*N],deg[N];

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m; cin >> n >> m;
    FOR(v,0,n) tb[v] = -1, head[v] = -1;
    int k = 0;
    FOR(i,0,m){
        int t; cin >> t; st[i] = k;
        FOR(j,0,t){
            cin >> a[k]; tb[a[k]]=i;
            if(j && a[k] < a[k-1]){
                cout << "NO\n"; return 0;
            }
            k++;
        }
    }
    st[m]=k;
    int e = 0;
    auto add = [&](int u, int v){
        to[e] = v;
        nxt[e] = head[u];
        head[u] = e++;
        deg[v]++;
    };
    int c = 0, p = 0;
    FOR(v,0,n){
        if(tb[v] < 0){
            if(!c) continue;
            int  x = ord[0];
            while(p < st[x+1] && a[p] < v) p++;
            if(p == st[x+1]){cout << "NO\n"; return 0;}
            if(p > st[x])add(a[p],v);
        }else if(a[st[tb[v]]]==v){
            if(!c) p = st[tb[v]];
            ord[c++] = tb[v];
        }
    }
    FOR(i,0,m) FOR(j, st[i]+2, st[i+1]) add(a[j-1], a[j]);
    FOR(r,0,m-1){
        int x = ord[r], y = ord[r+1], q = st[y];
        for(int j = st[x]+1; j < st[x+1]; j++){
            while(q < st[y+1] && a[q] < a[j]) q++;
            if(q == st[y+1]){ cout << "NO\n"; return 0;}
            if(q > st[y]) add(a[q], a[j]);
        }
    }

    cout << "YES\n";
    FOR(i,0,m) cout << a[st[i]]<<' ';

    priority_queue<int, vector<int>, greater<int>> pq;
    FOR(v,0,n){
        if(!deg[v] && !(tb[v] >= 0 && a[st[tb[v]]] == v)) pq.push(v);
    }
    while(sz(pq)){
        int u = pq.top(); pq.pop();
        cout << u << ' ';
        for(int x = head[u]; ~x; x = nxt[x]){
            if(!--deg[to[x]]){
                pq.push(to[x]);
            }
        }
    }
    cout << '\n';
}
