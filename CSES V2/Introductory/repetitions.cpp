#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main(){
    string dna;
    cin >> dna;

    int temp = 1;
    int maxn = 0;
    for (int i = 0; i+1 < dna.length(); i++){
        if (dna[i] == dna[i+1]){
            temp++;
        }
        else{
            maxn = max(maxn, temp);
            temp = 1;
        }
    }
    maxn = max(maxn, temp);
    cout << maxn;
}   