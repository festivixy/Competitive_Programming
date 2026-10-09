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

int ox[6]={0,-1,-1,-1,0,0},oy[6]={0,0,0,-1,-1,-1},os[6]={0,0,-1,-1,-1,0};
int sd[12]={0,0,1,0,1,0,1,1,0,1,0,1};
//int c[3][N],f[3][N],fm[N],s[N],w[N];
//ll c[3][N],f[3][N],w[N];
//ll c[3][N],f[3][N],m;
ll c[3][N],f[3][N];
int fm[N],s[N];
//array<int,5> e[N];
array<ll,5> e[N];

void solve(){
    int n; cin >> n;
    FOR(i,0,n){
        //int x, y, t; cin >> x >> y >> t;
        ll x, y; int t; cin >> x >> y >> t;
        int j=t/2;
        f[0][i]=y+oy[j],f[1][i]=x+ox[j],f[2][i]=x+y+os[j];
        fm[i]=(t+1)/2%3,s[i]=sd[t];
        FOR(k,0,3) c[k][i] = 4*f[k][i]+2;
        c[fm[i]][i] += s[i] ? 1 : -1;
    }

    ll ans = 0;
    FOR(k,0,3){
        //FOR(i,0,n) w[i]=c[k][i];
        //sort(w,w+n);
        //FOR(i,0,n) ans += (ll)w[i]*(2*i-n+1);
        sort(c[k],c[k]+n);
        FOR(i,0,n) ans += c[k][i]*(2*i-n+1);
    }
    ans/=2;

    FOR(i,0,n){
        int k=fm[i];
        e[i]={k, f[k][i]+s[i], f[(k+1)%3][i], f[(k+2)%3][i], s[i]};
    }
    sort(e,e+n);
    for(int i = 0, j; i < n; i = j){
        //ll a=0, b=0;
        //for(j = i; j < n && e[j][0]==e[i][0] && e[j][1]==e[i][1]; j++) (e[j][4]?b:a)++;
        for(j = i; j < n && e[j][0]==e[i][0] && e[j][1]==e[i][1]; j++);
        //ans += a*b;
        //ans += a*(a-1)/2+a*b;
        //ans += a*(a-1)/2+a*b+b*(b-1)/2;
        //ans += (a+b)*(a+b-1)/2;
        ans += (ll)(j-i)*(j-i-1)/2;
        for(int l = i, r; l < j; l = r){
            //ll p=0,q=0;
            //for(r = l; r < j && e[r][2]==e[l][2] && e[r][3]==e[l][3]; r++) (e[r][4]?q:p)++;
            for(r = l; r < j && e[r][2]==e[l][2]; r++);
            //ans -= p*q;
            //ans -= p*q+p*(p-1)/2;
            //ans -= p*q+p*(p-1)/2+(q>1);
            //ans -= p*q+p*(p-1)/2+(q?q-1:0);
            //ans -= p*q+p*(p-1)/2+(q?q-1:0)+(q>2);
            //ans -= p*q+p*(p-1)/2+(q?q-1:0)+(q>2?q-2:0)+(q>3?q-3:0);
            //ans -= p*q;
            ans -= (ll)(r-l)*(r-l-1)/2;
        }
    }
    //ll m=0;
    //FOR(i,2,n){
    //FOR(i,1,n){
    //    m = e[i]==e[i-1] ? m+1 : 0;
    //    ans -= m;
    //}
    cout << ans << '\n';
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t; cin >> t;
    while(t--) solve();
}
