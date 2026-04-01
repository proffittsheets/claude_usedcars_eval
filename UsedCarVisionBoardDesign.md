### Developer Persona
You are an architect developing a website for a couple who is looking for a bespoke, high end report to buy their next car. It should be well-architected, yet easy to maintain. 

### Overview
This is a vision board project to help Molly & Justin Sheets, who are local to Atlanta, Georgia in the United States buy a used car 2 years from now. The goal of this project is to create a frontend that pulls pictures of possible cars (not used necessarily), feature data, and prices from websites, news articles, "top" lists across the web. 

There should be two sections of the website - The first, which should be developed as phase 1, will be options of makes and models from new cars in the last 5 years regardless of if used or not. This is to help us downselect on style and features.

Once we complete that part of the site we will pull real world data of used cars regularly and create scripts to enable this and refresh reports. 

### Brands / Car Mkaes We Like
Nissan, Toyota, Mercedes. Cars must be purchasable within the United States. 

### Brands to Exclude
Our max price range is $80,000. We are not looking for Ferrarri, McLarens. We also do not like Tesla. 

### Features of the Website & Reports
1. We want to have cars organized into low, medium, and high range options for both new and used cards. 
2. For new cars: We want to know prices, mileage, color options, number of seats. 
3. All cars must have an all wheel drive option. 
4. We are looking at sedans, SUVs, and minivans. 
5. We are looking for family focused vehicles with good safety ratings
6. Where possible, include if the car is a hybrid. We have a preference to get a environment friendly car
7. We want to be able to view both interiors and exteriors of the car on the website as still images which can be seen in a gallery or scroll view and loaded into full screen
8. The website should include links where possible to where source data came from for a car and link to its seller page both for new cars and used cars
9. We would also like additional minor details, as a dropdown or subpage for each car, that include things like cup holders, if there is heating in seats and whether it's all or only some of them, and details about the audio systems

### Code & Architecture
Any scripts should use python to pull data unless you recommend otherwise. These should be able to be run locally at first. As a later phase we would like to host this website in S3 and populate the data to S3 via a github action. We should also include a comprehensive set of tests for any data that is pulled. 

### Documentation
As part of creating the initial plan and documents we should keep a record of all data sources we will be pulling data from as it is pulled and researched. 

