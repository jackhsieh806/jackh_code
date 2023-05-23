class Solution {
public:
    int findPeakElement(vector<int>& nums) {

        int n = nums.size();
        int l = 0, r = n-1;
        int mid;

        if (n == 1)
            return 0;

        while (r >= l) {
            mid = (r+l)/2;
            if (mid == 0) {
                if (nums[mid+1] < nums[mid])
                    return mid;
                else 
                    return mid+1;
            }
            if (mid == n-1) {
                if (nums[mid-1] < nums[mid])
                    return mid;
                else
                     return mid-1;
                    
            }

            if (nums[mid+1] > nums[mid]) {
                l = mid+1;
            } else {
                 if (nums[mid-1] < nums[mid])
                    return mid;

                r = mid-1;
            }               

        }
        return mid;
        
    }
    int findPeakElement2(vector<int>& nums) {
        int res = 0;
        int i = res;
        int n = nums.size();

        if (n == 1)
            return 0;

        while (i < n - 1) {
            if (nums[i+1] < nums[i])
                return i;
            else
             i++;
        }
        return i;
        
    }
};
