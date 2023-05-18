class Solution {
public:

    int maximumBags(vector<int>& capacity, vector<int>& rocks, int additionalRocks) {
        int sz = capacity.size();
        int res = 0;

        for (int i = 0; i < sz; i++) {
            rocks[i] = capacity[i]- rocks[i];        
        }

        sort(rocks.begin(),rocks.end());

        for (auto a: rocks) {
            additionalRocks -= a;
            if (additionalRocks >= 0)
                res++;
            else
                return res;
        }

        return res;
    }

    int maximumBags_p(vector<int>& capacity, vector<int>& rocks, int additionalRocks) {
        priority_queue<int,vector<int>,greater<int>> q;
        int sz = capacity.size();
        int diff = 0;
        int res = 0;


        for (int i = 0; i< sz; i++) {
            diff = capacity[i]-rocks[i];
            if (diff <= 0)
                res++;
            else
                q.push(capacity[i]-rocks[i]);            
        }
        while (additionalRocks > 0 && !q.empty()) {
            additionalRocks -= q.top();
            q.pop();
            if (additionalRocks >= 0)
                res++;

        }

        return res;
    }
    
    
