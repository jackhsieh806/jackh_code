class Solution {
public:


    struct item {
        int i;
        int j;
        int sum;
        item(int i, int j,int sum) : i(i),j(j),sum(sum) {};
    };
    
    vector<vector<int>> kSmallestPairs(vector<int>& nums1, vector<int>& nums2, int k) {
        vector<vector<int>> result;

        auto comparex = [&](const item &a, const item &b) { return a.sum > b.sum;};

        int sz1 = nums1.size();
        int sz2 = nums2.size();
        //int i = 0, j = 0;
        priority_queue<item,vector<item>,decltype(comparex)> q(comparex);
        item x(0,0,0);
        

        for (int i = 0; i < min(sz1,k); i++) 
            q.push(item(i,0,nums1[i]+nums2[0]));
        
        while (k != 0 && q.size() > 0) {     
            x = q.top();
            result.push_back({nums1[x.i],nums2[x.j]});
            q.pop();
            if (x.j+1 < sz2)
                q.push(item(x.i,x.j+1,nums1[x.i]+nums2[x.j+1]));
            k--;
        }              
            
        return result;

    }

    vector<vector<int>> kSmallestPairs2(vector<int>& nums1, vector<int>& nums2, int k) {
        vector<vector<int>> result;
        vector<vector<int>> res;
        int sz1 = nums1.size();
        int sz2 = nums2.size();
        int i = 0, j = 0;
        vector<int> temp(2);
        priority_queue<pair<int,int>,vector<pair<int,int>>,cmp> q;
        //priority_queue<vector<int>> q;
        temp[0] = nums1[0];
        temp[1] = nums2[0];

        for (int i = 0; i < min(sz1,k); i++)
           for (int j = 0; j < min(sz2,k); j++)                
                q.push(make_pair(nums1[i],nums2[j]));
                
            
            //sort(result.begin(),result.end(),compare);
            while(!q.empty()) {
                result.push_back({q.top().first,q.top().second});
                q.pop();
                if (result.size() == k)
                    return result;
            }
            return result;

        return result;
    }
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
};
