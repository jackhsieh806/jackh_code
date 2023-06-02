class Solution {
public:
    int maximumDetonation(vector<vector<int>>& bombs) {
        int n = bombs.size();
        int res = 1;
        vector<vector<char>> bmap(n,vector<char>(n,0));

        for (int i = 0; i < n; i++) {
                long r_dis = pow(bombs[i][2],2);
            for (int j = 0; j< n; j++) {                
                if (i != j) {
                    long xw = pow(bombs[i][0]-bombs[j][0],2);
                    long yw = pow(bombs[i][1]-bombs[j][1],2);
                    if (r_dis >= xw+yw)
                        bmap[j][i] = 1;                    
                }
            }
        }

        for (int i = 0; i < n; i++) {   
            vector<int> visited(n,0);         
            res = max(res,1+bfs(i,visited,bmap));
            if (res == n)
                return res;
        }

        return res;



    }

    int bfs(int node, vector<int> &visited, vector<vector<char>> &bmap) {
        int n = visited.size();
        int res = 0;
        visited[node] = 1;
        for (int i = 0; i < n; i++) {
            if (bmap[i][node] == 1 && visited[i] == 0 ) {
               res += (1+bfs(i,visited,bmap));
            }
        }
        return res;

    }
};
