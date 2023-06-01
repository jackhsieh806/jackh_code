class Solution {
public:
    queue<pair<int,int>> q;
    int res;
    vector<vector<int>> dir{{-1,-1},{-1,0},{0,-1},{-1,1},{0,1},{1,1},{1,0},{1,-1}};
    int shortestPathBinaryMatrix(vector<vector<int>>& grid) {
        res = INT_MAX;
        int n = grid.size()-1;
        //pair<int,int> pos;

        if (grid[n][n] != 0 || grid[0][0] != 0)
            return -1;

        if (n == 0)
            return 1;

        grid[0][0] = 1;
        q.push(make_pair(0,0));
        while(!q.empty()) {
            
            for (int i = 0; i < q.size(); i++) {
                int x = q.front().first;
                int y = q.front().second;
                q.pop();
                int step = grid[y][x];

                for (auto d : dir) {
                    int xp = x+d[0];
                    int yp = y+d[1];
                    if (xp >= 0 && yp >= 0 && xp <= n && yp <= n) {                
                        if (grid[yp][xp] == 0){// || (grid[yp][xp] != 1 && grid[yp][xp] > step+1)) {
                            grid[yp][xp] = step+1;
                            if (xp == n && yp == n) {
                               return step+1;
                            }
                            q.push(make_pair(xp,yp));               
                        }
                    }
                }
            }
        }
        
        //bfs(0,0,n,1,grid);

        return (res == INT_MAX) ? -1 : res;

        
    }

    void bfs(int x,int y,int n,int step, vector<vector<int>>& grid) {
        //if (x < 0 || y < 0 || x > n || y > n)
          //  return;

        if (x == n && y == n) {
            res = min(res,step);
            return;
        }

        for (auto d : dir) {
            int xp = x+d[0];
            int yp = y+d[1];
            if (xp >= 0 && yp >= 0 && xp <= n && yp <= n) {                
                if (grid[yp][xp] == 0 || (grid[yp][xp] != 1 && grid[yp][xp] > step+1)) {
                    grid[yp][xp] = step+1;
                    bfs(xp,yp,n,step+1,grid);
                    //grid[yp][xp] = 0;
                }
            }
        }




    }
};
