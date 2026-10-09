#include "dreaming.h"
#include <bits/stdc++.h>
using namespace std;
#define FOR(i,a,b) for(int i=(a);i<(b);++i)
#define FORR(i,a,b) for(int i=(b)-1;i>=(a);--i)
#define all(x) begin(x),end(x)
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int,int> pii;
const int N=100005;

static int hd[N],nx[2*N],to[2*N],wt[2*N];
static int st[N],ord[N],par[N];
static ll d1[N],d2[N];
static bool vis[N];
static int cn;

static int go(int s,ll*d,bool keep){
    int top=0,far=s;
    cn=0;
    st[top++]=s; d[s]=0; par[s]=-1;
    while(top){
        int u=st[--top];
        vis[u]=true;
        if(keep) ord[cn]=u;
        ++cn;
        if(d[u]>d[far]) far=u;
        for(int e=hd[u];e!=-1;e=nx[e]) if(to[e]!=par[u]){
            par[to[e]]=u;
            d[to[e]]=d[u]+wt[e];
            st[top++]=to[e];
        }
    }
    return far;
}

int travelTime(int n,int m,int l,int a[],int b[],int t[]){
    memset(hd,-1,sizeof(int)*n);
    memset(vis,0,n);
    FOR(i,0,m){
        to[2*i]=b[i];   wt[2*i]=t[i];   nx[2*i]=hd[a[i]];     hd[a[i]]=2*i;
        to[2*i+1]=a[i]; wt[2*i+1]=t[i]; nx[2*i+1]=hd[b[i]];   hd[b[i]]=2*i+1;
    }

    ll ans=0,r1=-1,r2=-1,r3=-1;
    FOR(s,0,n){
        if(vis[s]) continue;
        int e1=go(s,d2,true);
        int k=cn;
        int e2=go(e1,d1,false);
        go(e2,d2,false);
        ans=max(ans,d1[e2]);
        ll r=d1[e2];
        FOR(j,0,k) r=min(r,max(d1[ord[j]],d2[ord[j]])); // ecc(u)=max(d(u,e1),d(u,e2))
        if(r>r1){r3=r2;r2=r1;r1=r;}
        else if(r>r2){r3=r2;r2=r;}
        else if(r>r3) r3=r;
    }

    // for(auto&u:component) if(u!=vert){adj[u].push_back(vert);adj[vert].push_back(u);len[u].push_back(L);len[vert].push_back(L);}
    // dfs3(0);dfs3(diamv);
    if(r2>=0) ans=max(ans,r1+r2+l);
    if(r3>=0) ans=max(ans,r2+r3+2LL*l);
    return (int)ans;
}