# Web Query

## Main features
- Search web using provided URL and display during card review. **Search the 1st Field** of current note
- Capture web image as card resource and save into note

![中文](https://zhuanlan.zhihu.com/p/32341193)

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/capture.gif)

## Installation
Use the installation code: 627484806

## Instructions
### Capture Image into Note Field
1. Click on button 'Capture' at the button
2. Crop the region of image
2. Select your note field and save
3. Cropped images will be saved to your resource folder of the profile 

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/save_cropped_img_to_field.png)


![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/save_cropped_img_to_field_2.png)

### Provider URL
This is an URL string you can customize in your settings. By default, 
This addon provide a value for Wikipedia: http://en.wikipedia.org/wiki/wiki.html?search=%s

Please note the "%s" at the end for "search=%s" which mean the parameter where addon will fill during the review.

#### Get Provider URL
You would be able to search the web for more provider URL patterns, or make your own just from your browser address bar:
1. Search images in www.bing.com for keyword "anki"
2. I got the URL like this from browser: https://cn.bing.com/images/search?q=anki&FORM=HDRSC2
3. Replace "anki" with "%s" in the parameters "search?q=anki"
4. The Provider URL is https://cn.bing.com/images/search?q=%s&FORM=HDRSC2

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/url_provider.png)

#### Update Provider URL
**Every Provider URL** should have and only one '%s' place holder.

1. Go to "Tool" > "Addons" and find "WebQuery"
2. Click on "Settings"
3. Find item "provider_url" and replace the value of its pair

### Other Setting
In the Addon setting window there more items for customization:
- query_on_question: default = true, set to false if you need the screen window to be shown only on answer page.

### More Screens
/* Bing Image*/
![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/main_bing.png)

/* Wikipedia Item*/

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/main_wiki.png)
