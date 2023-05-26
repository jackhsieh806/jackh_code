class Solution {
public:
    bool isValidSudoku(vector<vector<char>>& board) {
        vector<vector<pair<int,int>>> p(10);
        int w = board[0].size();
        int h = board.size();
        for (int y=0; y < h; y++)
            for (int x=0; x < w; x++) {
                int num = board[y][x] - '0';
                //printf("num = %d\r\n",num);
                if (num >0 && num <= 9)
                    p[num].push_back(make_pair(x,y));
            }
        for (int i = 1; i < 10; i++) {
            //sort(p[i].begin(),p[i].end(),compare);
            int sz = p[i].size();
            if (sz >= 2) {
                    vector<int> row_check(10,0);
                    vector<int> col_check(10,0);
                    vector<int> b3_check(10,0);
                    for (int j = 0; j < sz; j++) {
                        if (row_check[p[i][j].second]++ > 0)
                            return false;

                        if (col_check[p[i][j].first]++ > 0)
                            return false;

                        int idx = (p[i][j].first/3) + 3*(p[i][j].second/3);
                        //printf("idx[%d] = %d, x = %d, y = %d\r\n", i, idx,p[i][j].first,p[i][j].second );

                        if (b3_check[idx]++ > 0)
                            return false;

                    }
                }
            }
            //printf("sort pary\r\n");
        


        return true;
    }
    static bool compare(pair<int , int>p1,pair<int , int>p2) {
        if (p1.first == p2.first)
            return p2.second > p1.second;
            
        return p2.first > p1.first;
    }
};
