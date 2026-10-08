#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=2005;
#ifdef LOCAL
#define dbg(x) cerr<<#x<<"="<<(x)<<'\n'
#else
#define dbg(x)
#endif

int v[N],pos[N],cnt[N],seat[N],tr[8][8][8];
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void solve(){
    int n; cin >> n;
    auto ask = [&](int i, int j, int k){
        cout << "? " << i << ' ' << j << ' ' << k << '\n' << flush;
        int r; cin >> r;
        return r;
    };
    auto out = [&](){
        cout << "!";
        FOR(i,0,n) cout << ' ' << seat[i];
        cout << '\n' << flush;
    };

    if(n <= 8){
        FOR(i,0,n) FOR(j,i+1,n) FOR(k,j+1,n) tr[i][j][k] = ask(i,j,k);
        vector<int> g(n); iota(all(g),0);
        auto good = [&](){
            FOR(i,0,n) FOR(j,i+1,n) FOR(k,j+1,n){
                int a = pos[i], b = pos[j], c = pos[k];
                if(max({a,b,c})-min({a,b,c})+1 != tr[i][j][k]) return false;
            }
            return true;
        };
        do{
            FOR(i,0,n) pos[g[i]] = i;
            if(good()) break;
        }while(next_permutation(all(g)));
            FOR(i,0,n) seat[i] = g[i];
            out(); return;
    }

    auto run = [&](int u, int w)->bool{
        FOR(x,0,n+1) cnt[x] = 0;
        int mx = 0;
        FOR(x,0,n) if(x != u && x != w){
            v[x] = ask(u,w,x);
            cnt[v[x]]++;
            mx = max(mx,v[x]);
        }
        if(cnt[mx] == n-2) return false;
        FOR(x,0,n) pos[x] = -1;
        int e = -1; vector<int> z;
        FOR(x,0,n) if(x != u && x != w){
            if(v[x] == mx){ if(e < 0) e = x; }
            else if(v[x] == mx-1) z.push_back(x);
        }
        int far = mx-1, near, rn;
        pos[e] = 0;
        if(sz(z) >= 3){
            near = 1;
            rn = ask(e,u,z[0]) < mx ? u : w;
        }else{
            int zl = z[0], r = ask(e,u,zl);
            if(r > mx){pos[zl] = r-1; zl = z[1]; r = ask(e,u,zl);}
            pos[zl] = 1;
            if(r-1 == far){rn = w; near = ask(e,w,zl)-1;}
            else rn = u, near = r-1;
        }
        pos[rn] = near; pos[rn == u ? w : u] = far;
        int d = far-near+1;

        vector<int> in;
        vector<vector<int>> pr(n);
        FOR(x,0,n){
            if(x == u || x == w) continue;
            if(d >= 3 && v[x] == d){in.push_back(x); continue;}
            int k = v[x]-d;
            bool l = near-k >= 0, r = far+k < n;
            if(l && r) pr[k].push_back(x);
            else if(pos[x] < 0) pos[x] = l ? near-k : far+k;
        }
        FOR(k,1,n) if(sz(pr[k])){
            int x = pr[k][0], y = pr[k][1];
            if(pos[x] < 0 && pos[y] < 0) pos[x] = ask(e,rn,x) == near+1 ? near-k : far+k;
            if(pos[x] < 0) pos[x] = pos[y] == near-k ? far+k : near-k;
            else pos[y] = pos[x] == near-k ? far+k : near-k;
        }
        if(sz(in)){
            int s = 0;
            FOR(t,near+1,far) s += t;
            FOR(i,0,sz(in)-1){
                pos[in[i]] = ask(e,rn,in[i])-1;
                s -= pos[in[i]];
            }
            pos[in.back()] = s;
        }
        FOR(x,0,n) seat[pos[x]] = x;
        return true;
    };

    vector<int> id(n); iota(all(id),0); shuffle(all(id),rng);
    int a = id[0], b = id[1];
    int m = min(n-3, max(3,(int)sqrt(1.5*n)));
    vector<pii> sm;
    FOR(i,2,2+m) sm.push_back({ask(a,b,id[i]),id[i]});
    sort(all(sm),greater<pii>());
    int x1 = sm[0].second, y = a;
    FOR(i,1,m) if(sm[i].first < sm[0].first && ask(x1,sm[i].second,a) <= sm[0].first){
        y = sm[i].second;
        break;
    }
    if(!run(x1,y)){
        int c = 0;
        while(c == x1 || c == y) c++;
        run(x1,c);
    }
    out();
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t; cin >> t;
    while(t--) solve();
}
