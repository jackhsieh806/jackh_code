    vector<int> findDiagonalOrder(vector<vector<int>>& mat) {
        vector<int> res;
        bool dirup = true;
        int count = 0;
        int x = 0, y = 0;
        int m = mat[0].size();
        int n = mat.size();
        while(count < m*n) {
            res.push_back(mat[y][x]);
            //printf("push [%d][%d], dir = %d\r\n",x,y, dirup);
            count++;
            if (dirup == true && x == m-1) {
                y = y+1;
                dirup = false;
            } else if (dirup == false && y == n -1) {
                dirup = true;
                x=x+1;
            } else if (dirup == true && y == 0) {
                dirup = false;
                x = x+1;
            } else if (dirup == false && x == 0) {                
                y = y+1;
                dirup = true;
            }  else {
                if (dirup == false) {
                    x = x - 1;
                    y = y + 1;
                } else if (dirup == true) {
                    x = x+1;
                    y= y-1;
                }
            }
        }

        return res;
    }
