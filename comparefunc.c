    struct cmp {
        bool operator() (pair<int, int> &a, pair<int, int> &b) {
            return a.first + a.second > b.first + b.second;
        }
    };
    static bool compare2(pair<int,int> &n1,pair<int,int> &n2) {
        return n1.first+n1.second < n2.first+n2.second;
    }    

    static bool compare(vector<int>& n1,vector<int>& n2) {
        return n1[0]+n1[1] < n2[0]+n2[1];
    }
