To start a new dictionary:
->  crate one with new_dictionary.sql
    example: sqlite3 crazy_dict.sqlite < new_dictionary.sql
->  specify the file name and folder in paths.py
->  You are ready to start: execute CrazyDic_app.py! 

JAVASCRIPT

Blueprints
<ol id="parent_id"> # this is the parent element contains a list of instances the con

    # HERE all <li> elements are added from blueprint

    <li class="blueprint"> # this is the blueprint
    <button> # this button adds new instances from blueprint
</ol>

Calling newInstance(...parent_id) in button
parent_id are all id of containers targeted (ol)

At start provide a script with editTemplate(id, object_list)
id: parent_id
object_list: [{name: name_content, subName1: [{}, ...], subName2: [...], ...}]
ALL lists contain: objects or strings
All objects contain: AT LEAST name

Substitutiions made by newInstance and editTemplate
#number-<parent_id># -> nuber of <li> element in <ol>
#parent_id# -> '' or name_content in editTemplate

For subChilds
#number-<parent_id>-<parent_number>-subName#
#<parent_id>-<parent_number>-subName#
ALL parent_id in subChilds: <parent_id>-<parent_number>-subName

<ol id="ol-parent">
    <li class="blueprint"> # this is the blueprint
        <p> nuber: #number-ol-parent#
        <p> content: #ol-parent-#

        # at some point inside blueprint of <olid="ol-parent">:
        <ol id="ol-parent-#number-ol-parent#-subName">
            <li class="blueprint">
            <p> nuber: #number-ol-parent-#number-ol-parent#-subName#
            <p> content: #ol-parent-#number-ol-parent#-subName#
            <button>
    <button> # this button adds new instances from blueprint
</ol>