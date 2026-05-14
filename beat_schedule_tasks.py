from website.tools.telegram_methods import SendCustomicReportMessageThread


def update_basalam_request_capacity(users):
    counter_error = 0
    counter_pass = 0
    counter_premium = 0
    counter_normal = 0
    counter_total_usage = 0

    for user in users:
        print("bs_request capacity ##########################################")
        print(f"user: {user}")
        try:
            user_bs_capacity = user.basalam_abilities
            shop_plan = None         

            # handle the case if user instance does not have basalam abilities
            if not user_bs_capacity:
                counter_pass += 1
                print(f"user: {user}, does not have basalam_abilities, pass")
                continue

            if seller_profile := getattr(user, "seller_profile", None):
                if shop := getattr(seller_profile, "shop", None):
                    shop_plan = shop.plan
                    if shop_plan.slug != "free":
                        counter_total_usage += 5 - user_bs_capacity.basalam_request_capacity
                        user_bs_capacity.basalam_request_capacity=5
                        user_bs_capacity.save()
                        counter_premium += 1
                        print(f'capacity of premium user: {user}, shop plan: {shop_plan} updated to {user_bs_capacity.basalam_request_capacity}')
                        continue       

        except Exception as e:
            counter_error += 1
            print("###########################")
            print(e)
            print("###########################")

    # Send progress status telegram notification
    SendCustomicReportMessageThread(
        type="ظرفیت باسلام",
        thread_number=1816,
        message="Basalam request capacity updated!\n\n" \
            + f"total users: {users.count()}" + "\n" \
            + f"total premium updates: {counter_premium}" + "\n" \
            + f"total normal updates: {counter_normal}" + "\n" \
            + f"total pass, (no basalam abilities): {counter_pass}" + "\n" \
            + f"total usage: {counter_total_usage}" + "\n" \
            + f"total errors: {counter_error}" + "\n\n" 
    ).start()
