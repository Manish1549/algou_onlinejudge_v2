#include <bits/stdc++.h>
using namespace std;
int const N = 100;
int adjMatrix[N+1][N+1];
vector<vector<int>> graph;

int main() {
  int n;
  cin>>n;
  int a;
  //adjMatrx
  for(int i =1;i<=n;i++){
    graph.push_back(vector<int>());
    for(int j =1;j<=n;j++){
      cin>>a;
      adjMatrix[i][j] = a;
      if(a==1){
        graph[i-1].push_back(j);
      }
    }
  }
  
  //adjList or Graph 
  
  // Print the adjacency list
    for (int i = 0; i <n; ++i) {
        cout <<i+1<< ":";
        for (int neighbor : graph[i]) {
            cout << neighbor << "";
        }
        cout << endl;
    }

  

  return 0;

}