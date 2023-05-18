class Solution {
public:
    string convert(string s, int numRows) {
        vector<string> zig(numRows);
        int sz = s.size();
        int idx = 0;
        bool down = true;
        string res;
        if (numRows == 1)
            return s;

        for (int i = 0; i < sz; i++) {
            if (down == true ) {
                if (idx < numRows) {
                    zig[idx].push_back(s[i]);
                    idx++;
                } else {
                    idx = numRows - 2;                    
                    zig[idx].push_back(s[i]);
                    idx--;
                    down = false;
                }
            } else if (down == false) {
                if (idx >= 0) {
                    zig[idx].push_back(s[i]);
                    idx--;
                } else {
                    idx = 1;
                    zig[idx].push_back(s[i]);
                    idx++;
                    down = true;
                }
            }

        }

        for (auto a : zig) {
            res = res + a;
        }
        return res;

    }
};
